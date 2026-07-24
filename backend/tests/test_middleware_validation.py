import pytest
from flask import Flask, jsonify, request
from middleware.validation import validate_json, compile_schema


@pytest.fixture
def validation_app():
    app = Flask(__name__)
    app.config['TESTING'] = True

    @app.route('/test-basic', methods=['POST'])
    @validate_json({
        'title': {'type': str, 'required': True, 'min_length': 3, 'max_length': 50},
        'age': {'type': int, 'required': False, 'min': 18},
        'is_active': {'type': bool, 'required': False}
    })
    def test_basic():
        return jsonify({'status': 'ok'})

    @app.route('/test-strict-extra', methods=['POST'])
    @validate_json({
        'name': {'type': str, 'required': True}
    }, allow_extra_fields=False)
    def test_strict_extra():
        return jsonify({'status': 'ok'})

    @app.route('/test-advanced', methods=['POST'])
    @validate_json({
        'email': {'type': str, 'pattern': r'^[\w\.-]+@[\w\.-]+\.\w+$'},
        'tags': {'type': list, 'item_type': str},
        'user': {
            'type': dict,
            'schema': {
                'role': {'type': str, 'allowed_values': ['admin', 'user']}
            }
        }
    })
    def test_advanced():
        return jsonify({'status': 'ok'})

    return app


def test_validation_basic_success(validation_app):
    client = validation_app.test_client()
    resp = client.post('/test-basic', json={'title': '  Hello World  ', 'age': 25, 'is_active': True})
    assert resp.status_code == 200


def test_empty_json_object_allowed_if_not_required(validation_app):
    client = validation_app.test_client()
    resp = client.post('/test-strict-extra', json={'name': 'Alice'})
    assert resp.status_code == 200


def test_strict_bool_vs_int_type_validation(validation_app):
    client = validation_app.test_client()
    # Passing bool True for age (which requires int) should fail!
    resp = client.post('/test-basic', json={'title': 'Valid Title', 'age': True})
    assert resp.status_code == 400
    assert "must be of type int" in resp.json['details'][0]


def test_extra_fields_rejection(validation_app):
    client = validation_app.test_client()
    resp = client.post('/test-strict-extra', json={'name': 'Alice', 'admin': True})
    assert resp.status_code == 400
    assert "Unexpected field 'admin'" in resp.json['details'][0]


def test_pattern_and_list_item_and_nested_schema(validation_app):
    client = validation_app.test_client()

    # Invalid email pattern & invalid list item
    resp = client.post('/test-advanced', json={
        'email': 'not-an-email',
        'tags': ['python', 123],
        'user': {'role': 'invalid_role'}
    })
    assert resp.status_code == 400
    details = resp.json['details']
    assert len(details) == 3


def test_schema_startup_compilation():
    schema = {'name': {'type': str, 'pattern': r'^[a-z]+$'}}
    compiled = compile_schema(schema)
    assert '_compiled_pattern' in compiled['name']
