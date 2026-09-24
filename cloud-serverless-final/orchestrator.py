import logging

import azure.durable_functions as df


# ============================================================
# LOGGING / APPLICATION INSIGHTS
# ============================================================

def log_event(level, message, **dimensions):
    """
    Registra eventos estruturados para o Application Insights.
    As dimensoes ficam disponiveis em custom_dimensions.
    """
    extra = {
        "custom_dimensions": dimensions
    }

    getattr(logging, level)(
        message,
        extra=extra
    )


# ============================================================
# ORCHESTRATOR
# ============================================================

def orchestrator_function(context: df.DurableOrchestrationContext):

    # --------------------------------------------------------
    # RECEBER PEDIDO
    # --------------------------------------------------------

    order = context.get_input()

    order_id = order.get("order_id")

    log_event(
        "info",
        "Pedido recebido",
        event="order_received",
        activity="orchestrator",
        order_id=str(order_id),
        status="RECEIVED"
    )

    # --------------------------------------------------------
    # ORQUESTRACAO INICIADA
    # --------------------------------------------------------

    log_event(
        "info",
        "Orquestracao iniciada",
        event="orchestration_started",
        activity="orchestrator",
        order_id=str(order_id),
        status="STARTED"
    )

    # ========================================================
    # 1. VALIDAR PEDIDO
    # ========================================================

    validation_result = yield context.call_activity(
        "validate_order",
        order
    )

    # ========================================================
    # 2. VERIFICAR IDEMPOTENCIA
    # ========================================================

    idempotency_result = yield context.call_activity(
        "check_idempotency",
        order
    )

    # --------------------------------------------------------
    # PEDIDO JA FOI PROCESSADO
    # --------------------------------------------------------

    if idempotency_result.get("already_processed"):

        log_event(
            "info",
            "Pedido já processado. Encerrando orquestracao.",
            event="orchestration_already_processed",
            activity="orchestrator",
            order_id=str(order_id),
            idempotent=True,
            status="COMPLETED"
        )

        return {
            "status": "ALREADY_PROCESSED",
            "order_id": order_id
        }

    # ========================================================
    # 3. REGISTRAR PEDIDO COMO PROCESSANDO
    # ========================================================

    yield context.call_activity(
        "register_order",
        order
    )

    # ========================================================
    # 4. PROCESSAR PEDIDO COM RETRY
    # ========================================================

    retry_options = df.RetryOptions(
        first_retry_interval_in_milliseconds=5000,
        max_number_of_attempts=3
    )

    try:

        processing_result = yield context.call_activity_with_retry(
            "process_order_activity",
            retry_options,
            order
        )

    except Exception as e:

        # ----------------------------------------------------
        # RETRIES ESGOTADOS
        # ----------------------------------------------------

        log_event(
            "error",
            "Pedido falhou apos esgotar os retries",
            event="order_processing_retries_exhausted",
            activity="orchestrator",
            order_id=str(order_id),
            status="FAILED",
            error=str(e)
        )

        # ----------------------------------------------------
        # PREPARAR INFORMAÇÕES DA FALHA
        # ----------------------------------------------------

        failure = {
            "order_id": order_id,
            "error": str(e)
        }

        # ====================================================
        # 5. REGISTRAR FALHA DEFINITIVA
        # ====================================================

        yield context.call_activity(
            "register_failure",
            failure
        )

        return {
            "status": "FAILED",
            "order_id": order_id,
            "error": str(e)
        }

    # ========================================================
    # 5. FINALIZAR PEDIDO
    # ========================================================

    finish_result = yield context.call_activity(
        "finish_order",
        order
    )

    # --------------------------------------------------------
    # ORQUESTRACAO CONCLUIDA
    # --------------------------------------------------------

    log_event(
        "info",
        "Orquestracao concluida com sucesso",
        event="orchestration_completed",
        activity="orchestrator",
        order_id=str(order_id),
        status="COMPLETED"
    )

    return {
        "status": "COMPLETED",
        "order_id": order_id
    }


# ============================================================
# REGISTRAR ORCHESTRATOR NO BLUEPRINT
# ============================================================

main = df.Blueprint()

main.orchestration_trigger(
    context_name="context"
)(orchestrator_function)