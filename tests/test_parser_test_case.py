from backend.models.parser_test_case import ParserTestCase


def test_parser_test_case_defaults():
    test_case = ParserTestCase(
        name="basic_test",
        raw_log="src_ip=10.0.0.1",
    )

    assert test_case.name == "basic_test"
    assert test_case.raw_log == "src_ip=10.0.0.1"
    assert test_case.expected_fields == {}
    assert test_case.description == ""


def test_parser_test_case_with_expected_fields():
    test_case = ParserTestCase(
        name="source_ip_test",
        raw_log="src_ip=10.0.0.1",
        expected_fields={
            "source_ip": "10.0.0.1",
        },
        description="Extract source IP",
    )

    assert test_case.expected_fields["source_ip"] == "10.0.0.1"
    assert test_case.description == "Extract source IP"