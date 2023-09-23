from starlette import status


def test_stripe_webhook_requires_stripe_sig_header(
    client,
    session_factory,
    backend_service_account,
    backend_service_account_headers,
):
    webhook_response = client.post(
        "/v1/stripe/webhook",
        json={
            "title": "Test",
            "description": "original description",
            "level": "warning",
        },
        headers={},
    )

    assert webhook_response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


def test_stripe_webhook_validates_signature(
    client,
    session_factory,
    backend_service_account,
    backend_service_account_headers,
):
    webhook_response = client.post(
        "/v1/stripe/webhook",
        json={
            "title": "Test",
            "description": "original description",
            "level": "warning",
        },
        headers={"stripe-signature": "t=123,v1=abc,v0=def,invalid-signature=123"},
    )

    assert webhook_response.status_code == status.HTTP_400_BAD_REQUEST
