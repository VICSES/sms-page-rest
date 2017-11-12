# Copyright 2017 David Tulloh This file is part of sms-page-rest.
# sms-page-rest is free software, you can distribute or modify it
# under the terms of the GNU Affero General Public License (AGPL-3).

import decimal
import sys
import os
import boto3
import botocore
from flask.json import JSONEncoder


# TODO: Split into multiple encoders, Decimal and set
class DecimalEncoder(JSONEncoder):
    def default(self, o): # pylint: disable=E0202
        if isinstance(o, decimal.Decimal):
            if o % 1 > 0:
                return float(o)
            else:
                return int(o)
        if isinstance(o, set):
            return list(o)
        return super(DecimalEncoder, self).default(o)


def get_table(name):
    aws = boto3.Session()

    if "pytest" in sys.modules:
        stage = "test"
        dynamodb = aws.resource('dynamodb', endpoint_url='http://localhost:8000')
    else:
        stage = os.environ.get('STAGE')
        dynamodb = aws.resource('dynamodb', region_name=os.environ.get('AWS_REGION'), use_ssl=True)

    return dynamodb.Table('sms-page-'+stage+'-'+name)


def lookup_member(member_id):
    if member_id is None:
        return None

    try:
        ret = get_table('member').get_item(Key={'member_id':int(member_id)})
    except botocore.exceptions.ClientError:
        return None # Member table not found

    return ret.get('Item') # None if not found


def lookup_role(name):
    if name is None:
        return None

    try:
        ret = get_table("role").get_item(Key={'name':name})
    except botocore.exceptions.ClientError:
        return None # Role table not found

    return ret.get('Item') # None if not found
