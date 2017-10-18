import json
import uuid
import decimal
import sys

import boto3
from boto3.dynamodb.conditions import Key, Attr


# table contact
#   phone_number (hash)
#   unit
#   member_id
# Global secondary index on contact
#   unit (partition), phone_number (range)

# table member
#   member_id (hash)
#   name
#   unit
#   roles
# Global secondary index on member
#   unit (partition), member_id (range)

# table role
#   name (hash)
#   permissions - list of strings

# table page_log
#   unit (hash)
#   timestamp (range)
#   phone_number
#   body

# table unit
#   name (hash)
#   capcode

tables = ['contact', 'member', 'unit', 'role', 'page_log']

aws = boto3.Session()
if "pytest" in sys.modules:
    dynamodb = aws.resource('dynamodb', endpoint_url='http://localhost:8000')
else:
    dynamodb = aws.resource('dynamodb', region_name='ap-southeast-2', use_ssl=True)

# Best run python3 -i dynamodb.py, then call functions by hand


# Helper class to convert a DynamoDB item to JSON.
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        return super(DecimalEncoder, self).default(o)

def gen_table_name(stage, table):
    return 'sms-page-'+stage+'-'+table


def create_contact(stage):
    table = dynamodb.create_table(
        TableName = gen_table_name(stage, 'contact'),
        KeySchema = [
            { 'AttributeName':'phone_number', 'KeyType':'HASH' },
        ],
        AttributeDefinitions = [
            { 'AttributeName':'phone_number', 'AttributeType':'S', },
            { 'AttributeName':'unit', 'AttributeType':'S', },
        ],
        ProvisionedThroughput = {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        },
        GlobalSecondaryIndexes = [ {
            "IndexName" : "contact_unit",
            "KeySchema" : [
                { 'AttributeName' : 'unit', 'KeyType' : 'HASH', },
                { 'AttributeName' : 'phone_number', 'KeyType' : 'RANGE', },
            ],
            'Projection' : { 'ProjectionType' : 'ALL' },
            'ProvisionedThroughput' : {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        } ],
    )
    print("Create contact status:", table.table_status)

# table member
#   member_id (hash)
#   name
#   roles
def create_member(stage):
    table = dynamodb.create_table(
        TableName = gen_table_name(stage, 'member'),
        KeySchema = [
            { 'AttributeName':'member_id', 'KeyType':'HASH' },
        ],
        AttributeDefinitions = [
            { 'AttributeName':'member_id', 'AttributeType':'N', },
            { 'AttributeName':'unit', 'AttributeType':'S', },
        ],
        ProvisionedThroughput = {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        },
        GlobalSecondaryIndexes = [ {
            "IndexName" : "member_unit",
            "KeySchema" : [
                { 'AttributeName' : 'unit', 'KeyType' : 'HASH', },
                { 'AttributeName' : 'member_id', 'KeyType' : 'RANGE', },
            ],
            'Projection' : { 'ProjectionType' : 'ALL' },
            'ProvisionedThroughput' : {
                'ReadCapacityUnits': 10,
                'WriteCapacityUnits': 10
            }
        } ],
    )
    print("Create member status:", table.table_status)


def create_page_log(stage):
    table = dynamodb.create_table(
        TableName = gen_table_name(stage, 'page_log'),
        KeySchema = [
            { 'AttributeName':'unit', 'KeyType':'HASH' },
            { 'AttributeName':'timestamp', 'KeyType':'RANGE' },
        ],
        AttributeDefinitions = [
            { 'AttributeName':'unit', 'AttributeType':'S' },
            { 'AttributeName':'timestamp', 'AttributeType':'N' },
        ],
        ProvisionedThroughput = {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    print("Create page_log status:", table.table_status)

def create_unit(stage):
    table = dynamodb.create_table(
        TableName = gen_table_name(stage, 'unit'),
        KeySchema = [
            { 'AttributeName':'name', 'KeyType':'HASH' },
        ],
        AttributeDefinitions = [
            { 'AttributeName':'name', 'AttributeType':'S' }
        ],
        ProvisionedThroughput = {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    print("Create unit status:", table.table_status)

def create_role(stage):
    table = dynamodb.create_table(
        TableName = gen_table_name(stage, 'role'),
        KeySchema = [
            { 'AttributeName':'name', 'KeyType':'HASH' },
        ],
        AttributeDefinitions = [
            { 'AttributeName':'name', 'AttributeType':'S' }
        ],
        ProvisionedThroughput = {
            'ReadCapacityUnits': 10,
            'WriteCapacityUnits': 10
        }
    )
    print("Create role status:", table.table_status)


def create(stage):
    try:
        create_contact(stage)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print("Contact table already exists")

    try:
        create_member(stage)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print("Member table already exists")

    try:
        create_page_log(stage)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print("Page log table already exists")

    try:
        create_unit(stage)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print("Unit table already exists")

    try:
        create_role(stage)
    except dynamodb.meta.client.exceptions.ResourceInUseException:
        print("Role table already exists")


def wait_until_active(stage):
    # Create takes a few seconds to process
    # Can't populate the table until the creation is complete
    while True:
        status = {}
        for t in tables:
            try:
                tname = gen_table_name(stage, t)
                status[t] = dynamodb.Table(t).table_status
            except dynamodb.meta.client.exceptions.ResourceNotFoundException:
                status[t] = 'NON-EXISTANT'

        print("Waiting for tables to become active: ", ", ".join(['{} == {}'.format(s, status[s]) for s in status]))

        still_waiting = False
        for s in status:
            if status[s] != 'ACTIVE':
                still_waiting = True

        if not still_waiting:
            break

def add_pagelog(stage, unit, timestamp, phone_number, body):
    table = dynamodb.Table(gen_table_name(stage, 'page_log'))
    table.put_item(Item={
        'unit':unit,
        'timestamp':timestamp,
        'phone_number':phone_number,
        'body':body
    })

def add_role(stage, name, permissions):
    table = dynamodb.Table(gen_table_name(stage, 'role'))
    table.put_item(Item={'name':name, 'permissions':permissions})

def populate_role(stage):
    table = dynamodb.Table(gen_table_name(stage, 'role'))

    table.put_item(Item={'name':'unit-admin', 'permissions':['myunit-unit-write', 'myunit-contact-write', 'myunit-contact-read', 'myunit-pagelog-read', 'myunit-member-write', 'myunit-member-read']})
    table.put_item(Item={'name':'site-admin', 'permissions':['unit-read', 'unit-write', 'contact-write', 'contact-read', 'pagelog-read', 'member-write', 'member-read']})
    table.put_item(Item={'name':'contact-maintainer', 'permissions':['myunit-contact-write', 'myunit-contact-read', 'myunit-pagelog-read']})
    table.put_item(Item={'name':'none', 'permissions':['myunit-pagelog-read']})

def populate(stage):
    # Initial data to allow first login and setup
    dynamodb.Table(gen_table_name(stage, 'unit')).put_item(Item={
        'name' : 'Bellarine',
        'capcode' : 76123,
    })
    dynamodb.Table(gen_table_name(stage, 'member')).put_item(Item={
        'unit'         : 'Bellarine',
        'name'         : 'David Tulloh',
        'member_id'    : 66103,
        'roles'  : json.dumps({
            'site-admin' : True,
        })
    })
    print("Table population complete")

def delete(stage):
    for t in tables:
        try:
            dynamodb.Table(gen_table_name(stage, t)).delete()
        except dynamodb.meta.client.exceptions.ResourceNotFoundException:
            pass # Already deleted, mission accomplished

def lookup_contact(num):
    table = dynamodb.Table('contact')
    response = table.query(
        KeyConditionExpression = Key('phone_number').eq(num),
        ConsistentRead = False,
    )
    for i in response[u'Items']:
        print(json.dumps(i, cls=DecimalEncoder))





#create()
#wait_until_active()
#populate()
