import azure.functions as func
import azure.durable_functions as df

import json
import logging

from activities import activities


app = df.DFApp()


# ============================================================
# SERVICE BUS TRIGGER
# ============================================================

@app.service_bus_topic_trigger(
    arg_name="message",
    topic_name="orders",
    subscription_name="orders-subscription",
    connection="SERVICE_BUS_CONNECTION"
)
@app.durable_client_input(client_name="client")
async def process_order(
    message: func.ServiceBusMessage,
    client
):

    body = message.get_body().decode("utf-8")

    order = json.loads(body)

    order_id = order.get("order_id")

    logging.info("================================")
    logging.info("Pedido recebido do Service Bus")
    logging.info("================================")

    logging.info(f"Order ID: {order_id}")
    logging.info(f"Cliente: {order.get('customer')}")
    logging.info(f"Produto: {order.get('product')}")
    logging.info(f"Quantidade: {order.get('quantity')}")

    instance_id = f"order-{order_id}"

    await client.start_new(
        "order_orchestrator",
        instance_id,
        order
    )

    logging.info(
        f"Orquestração iniciada: {instance_id}"
    )


# ============================================================
# DURABLE ORCHESTRATOR
# ============================================================

@app.orchestration_trigger(
    context_name="context"
)
def order_orchestrator(
    context: df.DurableOrchestrationContext
):

    order = context.get_input()

    order_id = order.get("order_id")

    # ========================================================
    # RETRY
    # ========================================================

    retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=5000,
        max_number_of_attempts=3
    )

    try:

        # ====================================================
        # 1. VALIDAR
        # ====================================================

        validation_result = yield context.call_activity_with_retry(
            "validate_order",
            retry_options,
            order
        )

        # ====================================================
        # 2. VERIFICAR IDEMPOTÊNCIA
        # ====================================================

        idempotency_result = yield context.call_activity_with_retry(
            "check_idempotency",
            retry_options,
            order
        )

        # ====================================================
        # PEDIDO JÁ PROCESSADO
        # ====================================================

        if idempotency_result["already_processed"]:

            logging.info(
                f"Pedido {order_id} já foi processado."
            )

            return {
                "order_id": order_id,
                "status": "ALREADY_PROCESSED"
            }

        # ====================================================
        # 3. REGISTRAR COMO PROCESSANDO
        # ====================================================

        yield context.call_activity_with_retry(
            "register_order",
            retry_options,
            order
        )

        # ====================================================
        # 4. PROCESSAR
        # ====================================================

        processing_result = yield context.call_activity_with_retry(
            "process_order_activity",
            retry_options,
            order
        )

        # ====================================================
        # 5. FINALIZAR
        # ====================================================

        finish_result = yield context.call_activity_with_retry(
            "finish_order",
            retry_options,
            order
        )

        # ====================================================
        # SUCESSO
        # ====================================================

        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "validation": validation_result,
            "idempotency": idempotency_result,
            "processing": processing_result,
            "finish": finish_result
        }

    except Exception as error:

        logging.error(
            f"Falha definitiva no pedido "
            f"{order_id}: {error}"
        )

        failure = {
            "order_id": order_id,
            "error": str(error)
        }

        # Registrar a falha
        yield context.call_activity(
            "register_failure",
            failure
        )

        return {
            "order_id": order_id,
            "status": "FAILED",
            "error": str(error)
        }


# ============================================================
# REGISTRAR ACTIVITIES
# ============================================================

app.register_functions(activities)