# Webhooks and Message Queues

Direction decides which side of the boundary code sits on. Whatever drives the application is an **inbound adapter**. Whatever the application drives sits behind a **port** with an outbound adapter.

| Situation | Who starts it | Where it goes |
|---|---|---|
| Third party sends us a webhook | They do | Inbound adapter |
| We consume from a queue | The message does | Inbound adapter, with no port |
| A timer fires a job | The clock does | Inbound adapter |
| We publish to a queue | We do | Port plus outbound adapter |
| We call a third-party API | We do | Port plus outbound adapter |

A runnable example of all of these is in [examples/refund-events/](../examples/refund-events/). Copy its structure, translated to the project's language. Read it in this order:

1. `src/refunds/domain/refund.py`
2. `src/refunds/application/record_refund_outcome.py`
3. `src/refunds/adapters/inbound/payment_webhook.py`
4. `src/refunds/application/publish_pending_events.py`
5. `src/refunds/adapters/inbound/queue_consumer.py`
6. `src/refunds/application/notify_customer.py`

```bash
cd examples/refund-events
PYTHONPATH=src:tests python3 -m unittest discover -s tests
```

## The flow

```
Provider --webhook--> [inbound: payment_webhook] --> record_refund_outcome
                                                      commits together:
                                                      refund state + outbox row

Timer --> [inbound: outbox_relay] --> publish_pending_events --> EventPublisher port
                                                                  --> [outbound: queue publisher] --> Queue

Queue --> [inbound: queue_consumer] --> notify_customer --> CustomerMailer port
                                                             --> [outbound: smtp] --> Customer
```

## Receiving a webhook

The inbound adapter does these steps in this order:

1. Read the raw bytes. The signature covers the exact body, so verify before parsing.
2. Compare signatures in constant time, such as `hmac.compare_digest`. A mismatch returns 401.
3. Parse the body. Malformed input returns 400.
4. Translate the vendor's event name into a domain value. An event type this service does not use returns 200, which stops retries.
5. Call one use case. Unexpected errors become a 5xx, which asks the provider to retry.

The status code tells the provider whether to retry:

| Result | Respond | Provider then |
|---|---|---|
| Processed, or already processed | 2xx | Stops |
| Bad signature or malformed body | 4xx | Follows its own policy; check its docs |
| Referenced record not here yet | Non-2xx | Retries, which handles early arrival |
| Our database or dependency failed | 5xx | Retries |

The use case receives domain values. Signature, headers, vendor event names and status codes stop at the adapter.

## Handling duplicates and out-of-order events

Providers and queues deliver at least once, and order is not guaranteed. Choose one approach per use case:

- **State change:** write the rule so that repeats and late arrivals change nothing, as `Refund.apply_outcome` does. No extra table is needed, and the behavior is tested as a business rule.
- **Side effect:** an email or an external call cannot be undone or absorbed by state, so record a handled key, as `notify_customer` does. Build the key from a stable event ID plus the operation name.

Check the key before the side effect and record it after success. A crash between the two repeats the effect, so a rare duplicate email is possible. Where a duplicate is unacceptable, such as a payment, pass the key to the third party as its idempotency key.

## Publishing to a queue: the outbox

Save the state change and the outgoing event in the same database transaction, using an `outbox` table. A separate relay then publishes pending rows and marks them published.

- A crash cannot lose an event, because the event commits with the state change.
- A queue outage cannot fail the webhook, because the request never touches the queue.
- The relay can publish twice, so consumers handle duplicates.

Use a stable event ID derived from the business fact, such as `refund-succeeded:<refund id>`. Redelivered copies then carry the same key.

## Consuming from a queue

The consumer is an inbound adapter. It owns everything about the queue:

1. Receive a delivery.
2. Decode it. A malformed message or unsupported version goes to the dead-letter queue immediately, because retrying cannot fix it.
3. Call one use case with a domain event.
4. On success, acknowledge.
5. On failure, retry. When attempts reach the limit, dead-letter with the reason, then acknowledge.

The use case takes a domain event and raises an error on failure. Receipts, ack, nack, attempt counts, retry limits and dead-lettering all live in the adapter.

## Where each piece goes

| Piece | Layer |
|---|---|
| Signature check | Inbound adapter |
| Vendor event names to domain values | Inbound adapter |
| Valid state changes | Domain |
| Domain event type (`RefundSucceeded`) | Domain |
| Outbox and handled-key tables | Outbound database adapter |
| Message JSON, type and version | One schema module in `adapters/` |
| Queue client | `adapters/`, shared by consumer and publisher |
| Ack, nack, retry limit, dead-letter | Inbound consumer adapter |
| Queue URL, secrets, topic names | Bootstrap |

The webhook server, the relay and the consumer usually run as separate processes, each with its own entry point through bootstrap, as in `src/bootstrap/wiring.py`. On a small deployment the relay may run as a background loop inside the server process.

The example's `with db.transaction()` block translates to the language's own form. In Go, for example, use `InTransaction(func(tx RefundTx) error)`, which commits on `nil` and rolls back on an error.

## Mapping to real brokers and frameworks

| Technology | Consumer adapter is | Acknowledge means | Retry and dead-letter |
|---|---|---|---|
| SQS | Polling loop or Lambda handler | Delete the message | Leave undeleted; a redrive policy owns the dead-letter queue |
| RabbitMQ | Channel consumer | `basic.ack` | `basic.nack`; a dead-letter exchange owns routing |
| Kafka | Consumer group loop | Commit the offset | No per-message nack; publish to retry and dead-letter topics |
| Google Pub/Sub | Subscriber callback | `ack()` | `nack()`; a dead-letter topic is set on the subscription |
| Celery, Sidekiq, BullMQ | Task or job function | Normal return | Framework retry settings |
| Spring `@KafkaListener` or `@RabbitListener` | The annotated method | Container-managed or manual | Container error handler |

Where the broker owns retries or dead-lettering, the adapter configures it and reports failure instead of counting attempts. Keep the task or listener function thin: decode, call one use case, report the result. Keep framework task decorators out of `application` and `domain`.

## Boundary Map rows

```markdown
| Port | Adapter | Touches | Fake for tests |
|---|---|---|---|
| Database | adapters/outbound/sqlite_database | refunds, outbox, handled tables | InMemoryDatabase |
| EventPublisher | adapters/outbound/queue_event_publisher | queue | recording publisher |
| CustomerMailer | adapters/outbound/smtp_mailer | SMTP | FakeMailer |

| Entry point | Inbound adapter | Calls |
|---|---|---|
| POST /webhooks/payments | adapters/inbound/payment_webhook | record_refund_outcome |
| relay timer | adapters/inbound/outbox_relay | publish_pending_events |
| queue message | adapters/inbound/queue_consumer | notify_customer |
```

## Tests that catch the real failures

| Layer | Required cases |
|---|---|
| Domain | Duplicate outcome, late outcome after a final state |
| Application | Duplicate event gives one side effect; failed side effect stays retryable; queue outage keeps the event pending |
| Webhook adapter | Bad signature rejected before parsing, malformed body, unused event type, record not found, dependency error |
| Consumer adapter | Success acknowledges, malformed goes straight to dead-letter, retry until the limit, then dead-letter |
| Outbound contract | Rollback removes state and outbox row together; message redelivers after a nack |
| End to end | Out-of-order and duplicate webhooks plus redelivery produce exactly one email |
