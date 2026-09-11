from backend.models.parser_validation_request import (
    ParserValidationRequest,
)


def test_parser_validation_request():
    request = ParserValidationRequest(
        definition={
            "parser_name": "device_parser",
            "format_type": "key_value",
            "mappings": {
                "src_ip": "source_ip",
            },
        },
        raw_log="src_ip=10.0.0.1",
    )

    assert request.definition.parser_name == "device_parser"
    assert request.raw_log == "src_ip=10.0.0.1"


def test_parser_validation_request_defaults():
    request = ParserValidationRequest(
        definition={
            "parser_name": "device_parser",
            "format_type": "plain_text",
        },
        raw_log="normal log",
    )

    assert request.definition.mappings == {}
    assert request.raw_log == "normal log"