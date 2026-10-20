# REST API

The REST API accepts document images, runs OCR extraction, and returns structured field values.

Swagger UI: `/api/rest/swagger/`  
ReDoc: `/api/rest/redoc/`

---

## Authentication

All endpoints require authentication. Three methods are supported:

| Method | Header |
|---|---|
| Basic | `Authorization: Basic <base64(username:password)>` |
| Token | `Authorization: Token <token>` |
| Session | Django session cookie (browser / admin) |

Unauthenticated requests receive `401 Unauthorized`.

---

## POST /api/analyze/

Submit a document image for analysis.

**Query parameters**

| Parameter | Values | Default |
|---|---|---|
| `sync` | `true` / `1` | — |

When `?sync=true` the task runs in-process and the response contains the full result (HTTP 200). Without it the task is queued via Celery and the response contains only the `job_id` (HTTP 202).

**Request body** — `multipart/form-data` or JSON

| Field | Type | Required | Notes |
|---|---|---|---|
| `image_file` | File upload | One of three required | Uploaded image file |
| `image_url` | URL string | One of three required | Image fetched by the server |
| `image_base64` | String | One of three required | Base64-encoded image, optional `data:…;base64,` prefix |
| `document_type` | String | Yes | `DocumentType.code`, e.g. `PAS` |
| `country` | String | Yes | `Country.code2`, e.g. `IT` |
| `callback_url` | URL string | No | Called via POST with the result payload when the job completes |
| `validation_mode` | String | No | See [Validation modes](#validation-modes). Default: `fall_back_to_best_match` |

**Synchronous response — HTTP 200**

```json
{
  "job_id": "5ef25336-94ab-4819-9c25-510cb88914ad",
  "status": "completed",
  "document_type": "PAS",
  "country": "IT",
  "validation_mode": "fall_back_to_best_match",
  "version": "2024",
  "version_matched": true,
  "attributes": [
    {"attribute_name": "first_name", "extracted_value": "MARIO"},
    {"attribute_name": "last_name",  "extracted_value": "ROSSI"},
    {"attribute_name": "document_number", "extracted_value": "AA1234567"}
  ],
  "error": null
}
```

**Asynchronous response — HTTP 202**

```json
{"job_id": "5ef25336-94ab-4819-9c25-510cb88914ad"}
```

**Error responses**

| Status | Cause |
|---|---|
| 400 | Missing or invalid fields (see error body for detail) |
| 401 | Not authenticated |

---

## GET /api/analyze/{job_id}/

Poll the status of a submitted job.

**Response**

Same shape as the synchronous `POST` response. `version`, `version_matched`, and `attributes` are `null` until the job reaches `completed`. `error` is populated (and `status` is `failed`) if processing fails.

**Status values:** `pending` → `running` → `completed` / `failed`

---

## Validation modes

The `validation_mode` field controls how the extraction pipeline handles attribute values that do not match a `DocumentAttribute.validation_expression` regex:

| Value | Behaviour |
|---|---|
| `fall_back_to_best_match` | Non-conforming values are penalised in version scoring; the algorithm prefers a version where values match. Default. |
| `keep_value_mark_invalid` | Return the raw extracted value and mark it as invalid in the result. |
| `treat_as_not_found` | Discard the value; treat the attribute as not found for this job. |
| `fail_analysis` | Abort the job with `status: failed` if any attribute fails validation. |

---

## Callback

When `callback_url` is provided, the server sends a `POST` request to that URL on job completion. The request body is identical to the `GET /api/analyze/{job_id}/` response. No retries are attempted on failure.