import re
import logging

import marshmallow
import botocore
from boto3.dynamodb.conditions import Key
from flask import Blueprint, request, jsonify
from flask_restful import Resource, Api

from web.authorize import authorized, own_unit, has_permission, has_all
from web.models import get_table

rest_pages = Blueprint('rest_pages', __name__)

api = Api(rest_pages)


class AusMobileNumber(marshmallow.fields.Field):
    @staticmethod
    def _verify_aus_num(num):
        # Need to be an international format australian mobile number
        return re.fullmatch(r'61[45]\d{2}\d{3}\d{3}', num) is not None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.insert(0, self._verify_aus_num)


class ExistingUnit(marshmallow.fields.Field):
    @staticmethod
    def _verify_unit_exists(name):
        try:
            unit_response = get_table('unit').query(
                KeyConditionExpression = Key('name').eq(name),
                ConsistentRead = False,
            )
            return not unit_response.get('Count') == 0
        except botocore.exceptions.ClientError:
            return False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.insert(0, self._verify_unit_exists)


class ExistingRoleSet(marshmallow.fields.Field):
    @staticmethod
    def _verify_role_exists(name_set):
        logger = logging.getLogger(__name__)
        logger.debug('VERIFY ROLE: %s', name_set)

        if name_set == set(['none']):
            # Dummy entry put in to avoid empty list
            return True

        for name in name_set:
            try:
                role_response = get_table('role').query(
                    KeyConditionExpression = Key('name').eq(name),
                    ConsistentRead = False,
                )
                if role_response.get('Count') == 0:
                    return False
            except botocore.exceptions.ClientError:
                return False
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.validators.insert(0, self._verify_role_exists)


class RoleSchema(marshmallow.Schema):
    name = marshmallow.fields.Str(required=True)
    permissions = marshmallow.fields.List(marshmallow.fields.Str, required=True)


class ContactSchema(marshmallow.Schema):
    phone_number = AusMobileNumber(required=True)
    unit = ExistingUnit(required=True)
    member_id = marshmallow.fields.Integer(required=True)


class MemberSchema(marshmallow.Schema):
    member_id = marshmallow.fields.Integer(required=True)
    name = marshmallow.fields.Str(required=True)
    unit = ExistingUnit(required=True)
    roles = ExistingRoleSet(required=True)


class UnitSchema(marshmallow.Schema):
    name = marshmallow.fields.Str(required=True)
    capcode = marshmallow.fields.Integer(required=True)


class PageLogSchema(marshmallow.Schema):
    phone_number = AusMobileNumber(required=True)
    unit = ExistingUnit(required=True)
    timestamp = marshmallow.fields.Decimal(required=True)
    body = marshmallow.fields.Str(required=True)


def assert_has_unit(name):
    try:
        ret = get_table('unit').get_item(Key={'name':name})
    except botocore.exceptions.ClientError as err:
        return {"error":"DatabaseError", "detail":err.response['Error']['Message']}, 500

    if ret.get('Item') is None:
        return {}, 404


class DynamoResource(Resource):
    # These attributes should be set by the implementing class
    table_name = None
    index_name = None # Optional, will be used for gets if included
    partition_key = None # Only needed for gets
    schema = None # Only needed for single_put()

    # Don't use standard methods, makes it hard to disable

    def _single_query(self, key):
        # Necessary when index lookup is performed
        qargs = {
            "KeyConditionExpression" : Key(self.partition_key).eq(key),
            "ConsistentRead" : False,
        }
        if self.index_name:
            qargs["IndexName"] = self.index_name # Optional

        try:
            response = get_table(self.table_name).query(**qargs)
        except botocore.exceptions.ClientError as err:
            return {"error":"DatabaseError", "detail":err.response['Error']['Message']}, 500

        if response.get('Count') == 0:
            return {}, 404
        elif response.get('Count') == 1:
            return response[u'Items'][0]
        else:
            return {
                "error":"DatabaseError",
                "detail":"single_get() returned multiple values. This function is not suitable for ranged values."
            }, 500

    def _single_get(self, key):
        try:
            ret = get_table(self.table_name).get_item(Key={self.partition_key:key})
        except botocore.exceptions.ClientError as err:
            return {"error":"DatabaseError", "detail":err.response['Error']['Message']}, 500

        if ret.get('Item'):
            return ret.get('Item'), 200
        else:
            return {}, 404

    def single_get(self, key):
        if self.schema is not None:
            # Integer types need to be cast before use
            field_type = self.schema._declared_fields.get(self.partition_key)
            if isinstance(field_type, marshmallow.fields.Integer):
                key = int(key)

        if self.index_name:
            return self._single_query(key)
        else:
            return self._single_get(key)

    def list_get(self, key):
        if self.schema is not None:
            # Integer types need to be cast before use
            field_type = self.schema._declared_fields.get(self.partition_key)
            if isinstance(field_type, marshmallow.fields.Integer):
                key = int(key)

        qargs = {
            "KeyConditionExpression" : Key(self.partition_key).eq(key),
            "ConsistentRead" : False,
        }
        if self.index_name:
            qargs["IndexName"] = self.index_name # Optional

        try:
            response = get_table(self.table_name).query(**qargs)
        except botocore.exceptions.ClientError as err:
            return {"error":"DatabaseError", "detail":err.response['Error']['Message']}, 500

        return response[u'Items']

    def single_put(self, item):
        # Must be a full insert or update, don't support partial updates

        if self.schema is not None:
            # TODO: Be consistent, numeric strings in, numeric strings out
            # TODO: When debugging schema failure should throw
            try:
                self.schema(strict=True).validate(item)
            except marshmallow.exceptions.ValidationError as err:
                # TODO: Use JSON Encoder
                return {"error":"ValidationError", "detail":err.normalized_messages()}, 422 # Unprocessable Entity

            # Integer types need to be cast before insertion
            for name, field in self.schema._declared_fields.items():
                if isinstance(field, marshmallow.fields.Integer):
                    item[name] = int(item.get(name))

        try:
            ret = get_table(self.table_name).put_item(Item=item, ReturnValues='ALL_OLD')
        except botocore.exceptions.ClientError as err:
            return {"error":"DatabaseError", "detail":err.response['Error']['Message']}, 500

        if ret.get('Attributes'):
            code = 200 # Update
        else:
            code = 201 # New

        return item, code


class UnitTable(DynamoResource):
    table_name = 'unit'
    partition_key = 'name'
    schema = UnitSchema

    @authorized(has_permission('unit-read'), own_unit())
    def get(self, unit):
        return self.single_get(unit)

    @authorized(has_permission('unit-write'), has_all(own_unit(), has_permission('myunit-unit-write')))
    def put(self, unit):
        item = request.form.copy()
        item["name"] = unit
        return self.single_put(item)


class ContactUnitTable(DynamoResource):
    table_name = 'contact'
    index_name = 'contact_unit'
    partition_key = 'unit'

    # Index resource, no adding entries
    @authorized(has_permission('contact-read'), has_all(own_unit(), has_permission('myunit-contact-read')))
    def get(self, unit):
        fault = assert_has_unit(unit)
        if fault:
            return fault
        return self.list_get(unit)


class PageLogUnitTable(DynamoResource):
    table_name = 'page_log'
    partition_key = 'unit'
    range_key = 'timestamp'

    @authorized(has_permission('pagelog-read'), has_all(own_unit(), has_permission('myunit-pagelog-read')))
    def get(self, unit):
        # TODO: pagination
        fault = assert_has_unit(unit)
        if fault:
            return fault
        return self.list_get(unit)


class ContactTable(DynamoResource):
    table_name = 'contact'
    partition_key = 'phone_number'
    schema = ContactSchema

    @authorized(has_permission('contact-read'), has_all(own_unit(), has_permission('myunit-contact-read')))
    def get(self, phone_num):
        return self.single_get(phone_num)

    @authorized(has_permission('contact-write'), has_all(own_unit(), has_permission('myunit-contact-write')))
    def put(self, phone_num):
        item = request.form.copy()
        item["phone_number"] = phone_num
        return self.single_put(item)


class RoleTable(DynamoResource):
    table_name = 'role'
    partition_key = 'name'
    schema = RoleSchema

    # Get only, roles are pre-populated by the system
    # No permission limitations, not sensative info
    def get(self, name):
        return self.single_get(name)


class MemberTable(DynamoResource):
    table_name = 'member'
    partition_key = 'member_id'
    schema = MemberSchema

    @authorized(has_permission('member-read'), has_all(own_unit(), has_permission('myunit-member-read')))
    def get(self, member_id):
        return self.single_get(member_id)

    @authorized(has_permission('member-write'), has_all(own_unit(), has_permission('myunit-member-write')))
    def put(self, member_id):
        item = {
            'member_id' : member_id,
            'name' : request.form.get('name'),
            'unit' : request.form.get('unit'),
            'roles' : set(dict(request.form).get('roles', ['none'])),
        }
        return self.single_put(item)


class MemberUnitTable(DynamoResource):
    table_name = 'member'
    index_name = 'member_unit'
    partition_key = 'unit'
    schema = MemberSchema

    @authorized(has_permission('member-read'), has_all(own_unit(), has_permission('myunit-member-read')))
    def get(self, unit):
        fault = assert_has_unit(unit)
        if fault:
            return fault
        return self.list_get(unit)


# TODO: POST for /rest/unit/<>/actions ??

api.add_resource(ContactTable, '/rest/contact/<string:phone_num>')
api.add_resource(RoleTable, '/rest/role/<string:name>')
api.add_resource(MemberTable, '/rest/member/<member_id>')
api.add_resource(UnitTable, '/rest/unit/<string:unit>')
api.add_resource(ContactUnitTable, '/rest/unit/<string:unit>/contacts')
api.add_resource(PageLogUnitTable, '/rest/unit/<string:unit>/pagelog')
api.add_resource(MemberUnitTable, '/rest/unit/<string:unit>/members')


@api.representation('application/json')
def output_json(data, code, headers=None):
    resp = jsonify(data)
    resp.status_code = code
    resp.headers.extend(headers or {})
    return resp
