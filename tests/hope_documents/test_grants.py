from hope_documents.grants import Grant


def test_grant_values_are_names():
    assert Grant.API_READ_ONLY.value == "API_READ_ONLY"
    assert Grant.API_PLAN_MANAGE.value == "API_PLAN_MANAGE"
    assert Grant.API_OCR_EXTRACT.value == "API_OCR_EXTRACT"


def test_grant_choices():
    choices = Grant.choices()
    assert choices == (
        ("API_READ_ONLY", "Api Read Only"),
        ("API_PLAN_MANAGE", "Api Plan Manage"),
        ("API_OCR_EXTRACT", "Api Ocr Extract"),
    )
