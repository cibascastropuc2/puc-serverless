import json
import logging
import os

import azure.functions as func
import azure.durable_functions as df

from azure.data.tables import TableClient
from azure.core.exceptions import ResourceExistsError
from azure.servicebus import ServiceBusClient, ServiceBusMessage


activities = df.Blueprint()


# ============================================================
# CONFIGURAÇÃO DA TABELA
# ============================================================

TABLE_NAME = "Orders"


def get_table_client():
    """
    Cria o cliente da tabela Azure Table Storage.
    """

    connection_string = os.environ["AzureWebJobsStorage"]

    client = TableClient.from_connection_string(
        conn_str=connection_string,
        table_name=TABLE_NAME
    )

    try:
        client.create_table()
    except ResourceExistsError:
        pass

    return client


# ============================================================
# 1. VALIDAR PEDIDO
# ============================================================

@activities.activity_trigger(input_name="order")
def validate_order(order: dict):

    order_id = order.get("order_id")

    logging.info("================================")
    logging.info("Validando pedido")
    logging.info("================================")

    logging.info(f"Order ID: {order_id}")

    if not order.get("order_id"):
        raise ValueError(
            "order_id é obrigatório"
        )

    if not order.get("customer"):
        raise ValueError(
            "customer é obrigatório"
        )

    if not order.get("product"):
        raise ValueError(
            "product é obrigatório"
        )

    if not order.get("quantity"):
        raise ValueError(
            "quantity é obrigatório"
        )

    if order["quantity"] <= 0:
        raise ValueError(
            "quantity deve ser maior que zero"
        )

    logging.info(
        f"Pedido {order_id} validado com sucesso."
    )

    return {
        "status": "VALID",
        "order_id": order_id
    }


# ============================================================
# 2. VERIFICAR IDEMPOTÊNCIA
# ============================================================

@activities.activity_trigger(input_name="order")
def check_idempotency(order: dict):

    order_id = str(order["order_id"])

    logging.info("================================")
    logging.info("Verificando idempotência")
    logging.info("================================")

    logging.info(
        f"Verificando pedido {order_id}"
    )

    table_client = get_table_client()

    try:

        entity = table_client.get_entity(
            partition_key="orders",
            row_key=order_id
        )

        status = entity.get("status")

        logging.info(
            f"Pedido {order_id} já existe."
        )

        logging.info(
            f"Status atual: {status}"
        )

        return {
            "already_processed": status == "COMPLETED",
            "status": status,
            "order_id": order_id
        }

    except Exception:

        logging.info(
            f"Pedido {order_id} ainda não existe."
        )

        return {
            "already_processed": False,
            "status": "NEW",
            "order_id": order_id
        }


# ============================================================
# 3. REGISTRAR PEDIDO COMO PROCESSANDO
# ============================================================

@activities.activity_trigger(input_name="order")
def register_order(order: dict):

    order_id = str(order["order_id"])

    logging.info(
        f"Registrando pedido {order_id}."
    )

    table_client = get_table_client()

    entity = {
        "PartitionKey": "orders",
        "RowKey": order_id,
        "status": "PROCESSING"
    }

    try:

        table_client.create_entity(
            entity=entity
        )

        logging.info(
            f"Pedido {order_id} registrado."
        )

    except ResourceExistsError:

        logging.info(
            f"Pedido {order_id} já estava registrado."
        )

    return {
        "order_id": order_id,
        "status": "PROCESSING"
    }


# ============================================================
# 4. PROCESSAR PEDIDO
# ============================================================

@activities.activity_trigger(input_name="order")
def process_order_activity(order: dict):

    order_id = order.get("order_id")
    customer = order.get("customer")
    product = order.get("product")
    quantity = order.get("quantity")

    logging.info("================================")
    logging.info("Processando pedido")
    logging.info("================================")

    logging.info(f"Order ID: {order_id}")
    logging.info(f"Cliente: {customer}")
    logging.info(f"Produto: {product}")
    logging.info(f"Quantidade: {quantity}")

    # ========================================================
    # TESTE DE RETRY
    # ========================================================
    #
    # Para testar o Retry:
    #
    if order_id == 9999:
        raise Exception("Erro proposital para testar retry")
    #
    # Depois do teste, remova ou comente novamente.
    # ========================================================

    logging.info(
        f"Pedido {order_id} processado com sucesso."
    )

    return {
        "status": "PROCESSED",
        "order_id": order_id
    }


# ============================================================
# 5. FINALIZAR PEDIDO
# ============================================================

@activities.activity_trigger(input_name="order")
def finish_order(order: dict):

    order_id = str(order.get("order_id"))

    logging.info("================================")
    logging.info("Finalizando pedido")
    logging.info("================================")

    table_client = get_table_client()

    entity = {
        "PartitionKey": "orders",
        "RowKey": order_id,
        "status": "COMPLETED"
    }

    table_client.upsert_entity(
        entity=entity
    )

    logging.info(
        f"Pedido {order_id} finalizado."
    )

    return {
        "status": "COMPLETED",
        "order_id": order_id
    }


# ============================================================
# 6. REGISTRAR FALHA
# ============================================================

@activities.activity_trigger(input_name="failure")
def register_failure(failure: dict):

    order_id = str(failure["order_id"])

    logging.error(
        f"Pedido {order_id} falhou definitivamente."
    )

    # ========================================================
    # REGISTRAR FALHA NO AZURE TABLE
    # ========================================================

    table_client = get_table_client()

    entity = {
        "PartitionKey": "orders",
        "RowKey": order_id,
        "status": "FAILED",
        "error": failure.get(
            "error",
            "Unknown error"
        )
    }

    table_client.upsert_entity(
        entity=entity
    )

    # ========================================================
    # ENVIAR PARA FILA DE FALHAS
    # ========================================================

    connection_string = os.environ[
        "SERVICE_BUS_CONNECTION"
    ]

    failed_order = {
        "order_id": order_id,
        "status": "FAILED",
        "error": failure.get(
            "error",
            "Unknown error"
        )
    }

    with ServiceBusClient.from_connection_string(
        conn_str=connection_string
    ) as client:

        with client.get_queue_sender(
            queue_name="failed-orders"
        ) as sender:

            message = ServiceBusMessage(
                json.dumps(failed_order)
            )

            sender.send_messages(message)

    logging.error(
        f"Pedido {order_id} enviado para failed-orders."
    )

    return {
        "order_id": order_id,
        "status": "FAILED"
    }