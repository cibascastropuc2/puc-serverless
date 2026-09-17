import json
import logging
import os

import azure.functions as func
import azure.durable_functions as df

from azure.data.tables import TableClient
from azure.core.exceptions import ResourceExistsError
from azure.servicebus import ServiceBusClient, ServiceBusMessage


# ============================================================
# LOGGING / APPLICATION INSIGHTS
# ============================================================

def log_event(level, message, **dimensions):
    """
    Registra eventos estruturados para o Application Insights.
    As dimensões ficam disponíveis em custom_dimensions.
    """
    extra = {
        "custom_dimensions": dimensions
    }

    getattr(logging, level)(
        message,
        extra=extra
    )


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

    return TableClient.from_connection_string(
        conn_str=connection_string,
        table_name=TABLE_NAME
    )


# ============================================================
# 1. VALIDAR PEDIDO
# ============================================================

@activities.activity_trigger(input_name="order")
def validate_order(order: dict):

    order_id = order.get("order_id")

    # --------------------------------------------------------
    # EVENTO: VALIDAÇÃO INICIADA
    # --------------------------------------------------------

    log_event(
        "info",
        "Validando pedido",
        event="order_validation_started",
        activity="validate_order",
        order_id=str(order_id),
        status="STARTED"
    )

    try:

        # ----------------------------------------------------
        # VALIDAÇÕES
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # EVENTO: VALIDAÇÃO CONCLUÍDA
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido validado com sucesso",
            event="order_validation_completed",
            activity="validate_order",
            order_id=str(order_id),
            status="VALID"
        )

        return {
            "status": "VALID",
            "order_id": order_id
        }

    except Exception:

        # ----------------------------------------------------
        # EVENTO: VALIDAÇÃO FALHOU
        # ----------------------------------------------------

        log_event(
            "error",
            "Falha na validação do pedido",
            event="order_validation_failed",
            activity="validate_order",
            order_id=str(order_id),
            status="FAILED"
        )

        # Mantém a exceção para o Durable Functions
        # reconhecer a falha da Activity.
        raise


# ============================================================
# 2. VERIFICAR IDEMPOTÊNCIA
# ============================================================

@activities.activity_trigger(input_name="order")
def check_idempotency(order: dict):

    order_id = str(order["order_id"])

    # --------------------------------------------------------
    # EVENTO: VERIFICAÇÃO DE IDEMPOTÊNCIA INICIADA
    # --------------------------------------------------------

    log_event(
        "info",
        "Verificando idempotência",
        event="idempotency_check_started",
        activity="check_idempotency",
        order_id=order_id,
        status="STARTED"
    )

    table_client = get_table_client()

    try:

        # ----------------------------------------------------
        # CONSULTAR PEDIDO NO AZURE TABLE STORAGE
        # ----------------------------------------------------

        entity = table_client.get_entity(
            partition_key="orders",
            row_key=order_id
        )

        status = entity.get("status")

        # ----------------------------------------------------
        # PEDIDO JÁ PROCESSADO
        # ----------------------------------------------------

        if status == "COMPLETED":

            log_event(
                "info",
                "Pedido já processado",
                event="idempotency_check",
                activity="check_idempotency",
                order_id=order_id,
                idempotent=True,
                status="COMPLETED"
            )

            return {
                "already_processed": True,
                "status": "COMPLETED",
                "order_id": order_id
            }

        # ----------------------------------------------------
        # PEDIDO EXISTE, MAS AINDA NÃO FOI PROCESSADO
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido ainda não processado",
            event="idempotency_check",
            activity="check_idempotency",
            order_id=order_id,
            idempotent=False,
            status=status
        )

        return {
            "already_processed": False,
            "status": status,
            "order_id": order_id
        }

    except Exception:

        # ----------------------------------------------------
        # PEDIDO NÃO EXISTE
        # ----------------------------------------------------
        # É considerado um pedido novo.
        # Portanto:
        # idempotent = False
        # status = NEW
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido ainda não processado",
            event="idempotency_check",
            activity="check_idempotency",
            order_id=order_id,
            idempotent=False,
            status="NEW"
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

    # --------------------------------------------------------
    # EVENTO: REGISTRO INICIADO
    # --------------------------------------------------------

    log_event(
        "info",
        "Registrando pedido",
        event="order_registration_started",
        activity="register_order",
        order_id=order_id,
        status="STARTED"
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

        # ----------------------------------------------------
        # EVENTO: REGISTRO CONCLUÍDO
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido registrado",
            event="order_registration_completed",
            activity="register_order",
            order_id=order_id,
            status="PROCESSING"
        )

    except ResourceExistsError:

        # ----------------------------------------------------
        # PEDIDO JÁ ESTAVA REGISTRADO
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido já estava registrado",
            event="order_registration_already_exists",
            activity="register_order",
            order_id=order_id,
            status="PROCESSING"
        )

    except Exception:

        # ----------------------------------------------------
        # EVENTO: REGISTRO FALHOU
        # ----------------------------------------------------

        log_event(
            "error",
            "Falha ao registrar pedido",
            event="order_registration_failed",
            activity="register_order",
            order_id=order_id,
            status="FAILED"
        )

        raise

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

    # --------------------------------------------------------
    # EVENTO: PROCESSAMENTO INICIADO
    # --------------------------------------------------------

    log_event(
        "info",
        "Processando pedido",
        event="order_processing_started",
        activity="process_order_activity",
        order_id=str(order_id),
        status="PROCESSING"
    )

    try:

        # ----------------------------------------------------
        # INFORMAÇÕES DO PEDIDO
        # ----------------------------------------------------

        logging.info("================================")
        logging.info("Processando pedido")
        logging.info("================================")
        logging.info(f"Order ID: {order_id}")
        logging.info(f"Cliente: {customer}")
        logging.info(f"Produto: {product}")
        logging.info(f"Quantidade: {quantity}")

        # ====================================================
        # TESTE DE RETRY
        # ====================================================
        #
        # NÃO REMOVER AINDA.
        #
        # Quando order_id = 9999, será gerada uma exceção
        # proposital para testar o Retry do Durable Functions
        # e a observabilidade no Application Insights.
        #
        # ====================================================

        if order_id == 9999:
            raise Exception(
                "Erro proposital para testar retry"
            )

        # ----------------------------------------------------
        # EVENTO: PROCESSAMENTO CONCLUÍDO
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido processado com sucesso",
            event="order_processing_completed",
            activity="process_order_activity",
            order_id=str(order_id),
            status="PROCESSED"
        )

        return {
            "status": "PROCESSED",
            "order_id": order_id
        }

    except Exception:

        # ----------------------------------------------------
        # EVENTO: PROCESSAMENTO FALHOU
        # ----------------------------------------------------

        log_event(
            "error",
            "Falha no processamento do pedido",
            event="order_processing_failed",
            activity="process_order_activity",
            order_id=str(order_id),
            status="FAILED"
        )

        # Mantém a exceção para permitir o Retry.
        raise


# ============================================================
# 5. FINALIZAR PEDIDO
# ============================================================

@activities.activity_trigger(input_name="order")
def finish_order(order: dict):

    order_id = str(order.get("order_id"))

    # --------------------------------------------------------
    # EVENTO: FINALIZAÇÃO INICIADA
    # --------------------------------------------------------

    log_event(
        "info",
        "Finalizando pedido",
        event="order_completion_started",
        activity="finish_order",
        order_id=order_id,
        status="STARTED"
    )

    try:

        table_client = get_table_client()

        entity = {
            "PartitionKey": "orders",
            "RowKey": order_id,
            "status": "COMPLETED"
        }

        table_client.upsert_entity(
            entity=entity
        )

        # ----------------------------------------------------
        # EVENTO: PEDIDO FINALIZADO
        # ----------------------------------------------------

        log_event(
            "info",
            "Pedido finalizado",
            event="order_completed",
            activity="finish_order",
            order_id=order_id,
            status="COMPLETED"
        )

        return {
            "status": "COMPLETED",
            "order_id": order_id
        }

    except Exception:

        # ----------------------------------------------------
        # EVENTO: FINALIZAÇÃO FALHOU
        # ----------------------------------------------------

        log_event(
            "error",
            "Falha ao finalizar pedido",
            event="order_completion_failed",
            activity="finish_order",
            order_id=order_id,
            status="FAILED"
        )

        raise


# ============================================================
# 6. REGISTRAR FALHA
# ============================================================

@activities.activity_trigger(input_name="failure")
def register_failure(failure: dict):

    order_id = str(failure["order_id"])

    error_message = failure.get(
        "error",
        "Unknown error"
    )

    # --------------------------------------------------------
    # EVENTO: PEDIDO FALHOU DEFINITIVAMENTE
    # --------------------------------------------------------

    log_event(
        "error",
        "Pedido falhou definitivamente",
        event="order_failed",
        activity="register_failure",
        order_id=order_id,
        status="FAILED",
        error=error_message
    )

    try:

        # ====================================================
        # REGISTRAR FALHA NO AZURE TABLE STORAGE
        # ====================================================

        table_client = get_table_client()

        entity = {
            "PartitionKey": "orders",
            "RowKey": order_id,
            "status": "FAILED",
            "error": error_message
        }

        table_client.upsert_entity(
            entity=entity
        )

        # ----------------------------------------------------
        # EVENTO: FALHA REGISTRADA NO TABLE STORAGE
        # ----------------------------------------------------

        log_event(
            "info",
            "Falha registrada no Azure Table Storage",
            event="order_failure_table_recorded",
            activity="register_failure",
            order_id=order_id,
            status="FAILED"
        )

        # ====================================================
        # ENVIAR PARA FILA DE FALHAS
        # ====================================================

        connection_string = os.environ[
            "SERVICE_BUS_CONNECTION"
        ]

        failed_order = {
            "order_id": order_id,
            "status": "FAILED",
            "error": error_message
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

        # ----------------------------------------------------
        # EVENTO: PEDIDO ENVIADO PARA FAILED-ORDERS
        # ----------------------------------------------------

        log_event(
            "error",
            "Pedido enviado para failed-orders",
            event="failed_order_queued",
            activity="register_failure",
            order_id=order_id,
            status="FAILED"
        )

        return {
            "order_id": order_id,
            "status": "FAILED"
        }

    except Exception:

        # ----------------------------------------------------
        # EVENTO: FALHA AO REGISTRAR A FALHA
        # ----------------------------------------------------

        log_event(
            "error",
            "Falha ao registrar o pedido como FAILED",
            event="order_failure_registration_failed",
            activity="register_failure",
            order_id=order_id,
            status="FAILED",
            error=error_message
        )

        raise