import azure.functions as func
import azure.durable_functions as df

import json
import logging
import time

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

    start_time = time.perf_counter()

    try:

        # ====================================================
        # RECEBER PEDIDO
        # ====================================================

        body = message.get_body().decode("utf-8")
        order = json.loads(body)

        order_id = order.get("order_id")
        instance_id = f"order-{order_id}"

        logging.info(
            "Pedido recebido do Service Bus",
            extra={
                "custom_dimensions": {
                    "event": "order_received",
                    "order_id": str(order_id),
                    "instance_id": instance_id,
                    "customer": str(order.get("customer")),
                    "product": str(order.get("product")),
                    "quantity": str(order.get("quantity")),
                    "status": "RECEIVED"
                }
            }
        )

        # ====================================================
        # INICIAR ORQUESTRAÇÃO
        # ====================================================

        await client.start_new(
            "order_orchestrator",
            instance_id,
            order
        )

        # ====================================================
        # DURAÇÃO DO TRIGGER
        # ====================================================

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logging.info(
            "Orquestração iniciada com sucesso",
            extra={
                "custom_dimensions": {
                    "event": "orchestration_started",
                    "order_id": str(order_id),
                    "instance_id": instance_id,
                    "status": "STARTED",
                    "duration_ms": str(duration_ms)
                }
            }
        )

    except Exception as error:

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logging.error(
            "Falha ao iniciar processamento do pedido",
            extra={
                "custom_dimensions": {
                    "event": "order_trigger_failed",
                    "order_id": str(
                        locals().get(
                            "order_id",
                            "unknown"
                        )
                    ),
                    "status": "FAILED",
                    "duration_ms": str(duration_ms),
                    "error_type": type(error).__name__,
                    "error": str(error)
                }
            }
        )

        raise


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
    # LOG DE OBSERVABILIDADE
    # ========================================================

    if not context.is_replaying:

        logging.info(
            "Orquestração iniciada",
            extra={
                "custom_dimensions": {
                    "event": "orchestration_started",
                    "order_id": str(order_id),
                    "instance_id": context.instance_id,
                    "status": "STARTED"
                }
            }
        )

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

            if not context.is_replaying:

                logging.info(
                    "Pedido já foi processado",
                    extra={
                        "custom_dimensions": {
                            "event": "order_already_processed",
                            "order_id": str(order_id),
                            "instance_id": context.instance_id,
                            "status": "ALREADY_PROCESSED"
                        }
                    }
                )

            return {
                "order_id": order_id,
                "status": "ALREADY_PROCESSED"
            }

        # ====================================================
        # 3. REGISTRAR COMO PROCESSANDO
        # ====================================================

        register_result = yield context.call_activity_with_retry(
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

        if not context.is_replaying:

            logging.info(
                "Pedido processado com sucesso",
                extra={
                    "custom_dimensions": {
                        "event": "order_completed",
                        "order_id": str(order_id),
                        "instance_id": context.instance_id,
                        "status": "COMPLETED"
                    }
                }
            )

        return {
            "order_id": order_id,
            "status": "COMPLETED",
            "validation": validation_result,
            "idempotency": idempotency_result,
            "register": register_result,
            "processing": processing_result,
            "finish": finish_result
        }

    # ========================================================
    # FALHA DEFINITIVA
    # ========================================================

    except Exception as error:

        if not context.is_replaying:

            logging.error(
                "Falha definitiva no pedido",
                extra={
                    "custom_dimensions": {
                        "event": "order_failed",
                        "order_id": str(order_id),
                        "instance_id": context.instance_id,
                        "status": "FAILED",
                        "error_type": type(error).__name__,
                        "error": str(error)
                    }
                }
            )

        failure = {
            "order_id": order_id,
            "instance_id": context.instance_id,
            "error": str(error),
            "error_type": type(error).__name__
        }

        # ====================================================
        # REGISTRAR FALHA
        # ====================================================

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