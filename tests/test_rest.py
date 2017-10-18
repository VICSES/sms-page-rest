import pytest

import dynamodb
import responses

import decimal
import json
import jwt
import random
import time
from faker import Faker

fake = Faker()

@pytest.fixture
def clear_db():
    dynamodb.delete('test')
    dynamodb.create('test')
    #dynamodb.wait_until_active('test') # FIXME: Infinite loops

@pytest.fixture
def admin_token(token_secret):
    fullperm = {
        'member_id' : 1,
        'name' : 'Admin User',
        'unit' : 'test',
        'roles' : ['site-admin', 'unit-admin', 'contact-maintainer'],
        'permissions' : ['unit-read', 'unit-write', 'contact-write', 'contact-read', 'pagelog-read', 'member-write', 'member-read'],
        'iss' : 'sms-page',
        'exp' : int(time.time()+1000),
    }
    tok = jwt.encode(fullperm, token_secret, algorithm='HS256')
    return str(tok, 'utf-8')


def gen_phone():
    return '614'+str(random.randint(10000000, 99999999))

def gen_memberid():
    return str(random.randint(10000, 99999))
            

def test_unit_table(client, clear_db, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}

    u1 = client.put('/rest/unit/test', headers=headers, data={"capcode":"23"})
    assert(u1.status_code == 201)

    u2 = client.put('/rest/unit/test', headers=headers, data={"capcode":"32"})
    assert(u2.status_code == 200)

    g1 = client.get('/rest/unit/test', headers=headers)
    assert(g1.status_code == 200)
    j1 = json.loads(g1.data)
    assert(len(j1) == 2)
    assert(j1.get("name") == "test")
    assert(j1.get("capcode") == 32)


def test_unit_contacts(client, admin_token):
    # Test db error
    # Test empty query
    headers = {'Authorization':"Bearer " + admin_token}

    dynamodb.delete('test')

    # No table - error
    f1 = client.get('/rest/unit/test/contacts', headers=headers)
    assert(f1.status_code == 500)
    jf1 = json.loads(f1.data)
    assert(jf1.get("error") == "DatabaseError")
    assert(jf1.get("detail") == "Cannot do operations on a non-existent table")

    dynamodb.create('test')
    #dynamodb.wait_until_active('test') # TODO

    u1 = client.put('/rest/unit/test', data={"capcode":"23"}, headers=headers)
    assert(u1.status_code == 201)

    # No contacts - empty list
    ge = client.get('/rest/unit/test/contacts', headers=headers)
    assert(ge.status_code == 200)
    jge = json.loads(ge.data)
    assert(type(jge) is list)
    assert(len(jge) == 0)

    # Create fifty contacts
    for i in range(50):
        cr = client.put('/rest/contact/'+gen_phone(), data={"unit":"test", "member_id":gen_memberid()}, headers=headers)
        assert(cr.status_code == 201)

    # Fetch all contacts
    ga = client.get('/rest/unit/test/contacts', headers=headers)
    assert(ga.status_code == 200)
    jga = json.loads(ga.data)
    assert(type(jga) is list)
    assert(len(jga) == 50)

    # Non existant unit
    go = client.get('/rest/unit/other/contacts', headers=headers)
    assert(go.status_code == 404)


def test_contact_table(client, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}
    dynamodb.delete('test')

    # No table - error
    f1 = client.get('/rest/contact/61412123666', headers=headers)
    assert(f1.status_code == 500)
    jf1 = json.loads(f1.data)
    assert(jf1.get("error") == "DatabaseError")
    assert(jf1.get("detail") == "Cannot do operations on a non-existent table")


    dynamodb.create('test')
    # dynamodb.wait_until_active('test') # TODO

    u1 = client.put('/rest/unit/test', data={"capcode":"23"}, headers=headers)
    assert(u1.status_code == 201)

    data = {
        "member_id": 9998, 
        "unit": "test"
    }
    p1 = client.put('/rest/contact/61412123123', data=data, headers=headers)
    assert(p1.status_code == 201)
    j1 = json.loads(p1.data)
    assert(len(j1) == 3)
    assert(j1.get("member_id") == data.get("member_id"))
    assert(j1.get("unit") == data.get("unit"))
    assert(j1.get("phone_number") == '61412123123')

    g1 = client.get('/rest/contact/61412123123', headers=headers)
    assert(g1.status_code == 200)
    j1 = json.loads(g1.data)
    assert(len(j1) == 3)
    assert(j1.get("member_id") == data.get("member_id"))
    assert(j1.get("unit") == data.get("unit"))
    assert(j1.get("phone_number") == '61412123123')

    # Request non-existant entry
    g2 = client.get('/rest/contact/61412123666', headers=headers)
    assert(g2.status_code == 404)

    # Insert an entry without a unit
    data = {
        "member_id": 1123, 
        "unit": "badtest"
    }
    p2 = client.put('/rest/contact/61412123112', data=data, headers=headers)
    assert(p2.status_code == 422)
    j2 = json.loads(p2.data)
    assert(j2.get("error") == "ValidationError")
    assert(len(j2.get("detail")) == 1)
    assert(len(j2.get("detail").get('unit')) == 1)
    assert(j2.get("detail").get('unit')[0] == "Invalid value.")

    # Update an existing entry, inserted in p1
    data = {
        "member_id": 1113, 
        "unit": "test"
    }
    p3 = client.put('/rest/contact/61412123123', data=data, headers=headers)
    assert(p3.status_code == 200)
    j3 = json.loads(p3.data)
    assert(len(j3) == 3)
    assert(j3.get("member_id") == data.get("member_id"))
    assert(j3.get("unit") == data.get("unit"))
    assert(j3.get("phone_number") == '61412123123')

    # Update, change to invalid unit
    data = {
        "member_id": 1114, 
        "unit": "badtest"
    }
    p4 = client.put('/rest/contact/61412123123', data=data, headers=headers)
    assert(p4.status_code == 422)
    j4 = json.loads(p4.data)
    assert(j4.get("error") == "ValidationError")
    assert(len(j4.get("detail")) == 1)
    assert(len(j4.get("detail").get('unit')) == 1)
    assert(j4.get("detail").get('unit')[0] == "Invalid value.")


    g5 = client.get('/rest/contact/61412123123', headers=headers)
    j5 = json.loads(g5.data)
    assert(len(j5) == 3)
    assert(j5.get("member_id") == 1113)
    assert(j5.get("unit") == "test")
    assert(j5.get("phone_number") == '61412123123')

    # TODO
    # Invalid phone number - empty
    # Invalid phone number - short
    # Invalid phone number - long
    # Invalid phone number - letters
    # Invalid phone number - symbols
    # Invalid phone number - urlenc

    # TODO
    # Invalid member id - letters
    # Invalid member id - empty


def test_pagelog_table(client, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}
    dynamodb.delete('test')

    # No table - error
    f1 = client.get('/rest/unit/test/pagelog', headers=headers)
    assert(f1.status_code == 500)
    jf1 = json.loads(f1.data)
    assert(jf1.get("error") == "DatabaseError")
    assert(jf1.get("detail") == "Cannot do operations on a non-existent table")

    dynamodb.create_unit('test')
    u0 = client.put('/rest/unit/test', data={"capcode":"23"}, headers=headers)
    assert(u0.status_code == 201)

    # Now we should fail on our DB
    f4 = client.get('/rest/unit/test/pagelog', headers=headers)
    assert(f4.status_code == 500)
    jf4 = json.loads(f4.data)
    assert(jf4.get("error") == "DatabaseError")
    assert(jf4.get("detail") == "Cannot do operations on a non-existent table")

    dynamodb.create('test')
    #dynamodb.wait_until_active('test') # TODO

    # Create some dummy units
    units = ["test1", "test2", "test3"]
    for u in units:
        capcode = random.randint(1,1000)
        ur = client.put('/rest/unit/'+u, data={"capcode":capcode}, headers=headers)
        assert(ur.status_code == 201)

    phone_numbers = [ gen_phone() for x in range(10) ]

    # Create a pile of pagelog entries
    for i in range(500):
        unit = random.choice(units)
        phone_number = random.choice(phone_numbers)
        body = fake.text(max_nb_chars=200, ext_word_list=None)
        data = {"phone_number":phone_number,"unit":unit,"body":body}
        now = decimal.Decimal(time.time())

        dynamodb.add_pagelog('test', unit, now, phone_number, body)

    # Fetch the pagelogs back
    unit_data = []
    for u in units:
        gu = client.get('/rest/unit/'+u+'/pagelog', headers=headers)
        assert(gu.status_code == 200)
        unit_data.append(json.loads(gu.data))

    assert(len(unit_data) == 3)
    assert(len(unit_data[0]) + len(unit_data[1]) + len(unit_data[2]) == 500)

    for ud in unit_data:
        # Each list should have roughly 166 entries
        assert(len(ud) > 100)
        assert(len(ud) < 220)

    entry = unit_data[0][0]
    assert(entry.get("phone_number") is not None)
    assert(entry.get("unit") is not None)
    assert(entry.get("timestamp") is not None)
    assert(entry.get("body") is not None)

    go = client.get('/rest/unit/other/pagelog', headers=headers)
    assert go.status_code == 404


def test_role_table(client, clear_db, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}
    dynamodb.add_role('test', 'test', ["sing","dance","slide"])

    g1 = client.get('/rest/role/test', headers=headers)
    assert(g1.status_code == 200)
    j1 = json.loads(g1.data)
    assert(len(j1) == 2)
    assert(j1.get("name") == "test")
    assert(len(j1.get("permissions")) == 3)
    assert(set(j1.get("permissions")) == set(["sing","dance","slide"]))

    go = client.get('/rest/role/other', headers=headers)
    assert(go.status_code == 404)


def test_member_table(client, clear_db, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}
    # Prep
    u0 = client.put('/rest/unit/test', data={"capcode":"23"}, headers=headers)
    assert(u0.status_code == 201)
    for r in ['Grumio', 'Proteus', 'Fabian']:
        dynamodb.add_role('test', r, ["none"])

    p1 = client.put('/rest/member/55555', data={"name":"Jim Smith", "unit":"test", "roles":["Grumio","Fabian"]}, headers=headers)
    assert(p1.status_code == 201)

    p2 = client.put('/rest/member/55555', data={"name":"Jones Smith", "unit":"test", "roles":["Proteus","Fabian"]}, headers=headers)
    assert(p2.status_code == 200)

    g1 = client.get('/rest/member/55555', headers=headers)
    assert(g1.status_code == 200)
    j1 = json.loads(g1.data)
    assert(len(j1) == 4)
    assert(j1.get("member_id") == 55555)
    assert(j1.get("name") == "Jones Smith")
    assert(j1.get("unit") == "test")
    assert(len(j1.get("roles")) == 2)
    assert(set(j1.get("roles")) == set(["Proteus","Fabian"]))

    # TODO: Empty role set


def test_unit_member_table(client, clear_db, admin_token):
    headers = {'Authorization':"Bearer " + admin_token}
    u1 = client.put('/rest/unit/test', data={"capcode":"23"}, headers=headers)
    assert(u1.status_code == 201)
    roles = ['Grumio', 'Proteus', 'Fabian']
    for r in roles:
        dynamodb.add_role('test', r, ["none"])

    # No members - empty list
    ge = client.get('/rest/unit/test/members', headers=headers)
    assert(ge.status_code == 200)
    jge = json.loads(ge.data)
    assert(type(jge) is list)
    assert(len(jge) == 0)

    # Create fifty members
    for i in range(50):
        data = {
                "name":fake.name(),
                "unit":"test",
                "roles":random.sample(roles, random.randint(0,3))
        }
        cr = client.put('/rest/member/'+gen_memberid(), data=data, headers=headers)
        assert(cr.status_code == 201)
        # TODO: Will fail occasionally with duplicate memberid

    # Fetch all members
    ga = client.get('/rest/unit/test/members', headers=headers)
    assert(ga.status_code == 200)
    jga = json.loads(ga.data)
    assert(type(jga) is list)
    assert(len(jga) == 50)


@responses.activate
def permission_helper(client, userid, testlist):
    # testlist is a list of tuples
    # each tuple is (<Method>, <URL>, <Expected>)

    userdata_resp = {'userPrincipalName':'ses{}@members.ses.vic.gov.au'.format(userid)}
    responses.add(responses.GET, 'https://graph.microsoft.com/v1.0/me',
            json=userdata_resp, status=200)

    auth_resp = client.get('/authenticate', headers={'Authorization':"meh"})
    print('AR', auth_resp, auth_resp.data)
    auth_tok = json.loads(auth_resp.data).get('resource_token')

    headers = {'Authorization':"Bearer " + auth_tok}

    for (method, url, expected) in testlist:
        meth_func = getattr(client, method.lower())
        res = meth_func(url, headers=headers, data={'unit':'test'})
        print("PH", method, url, res.status_code, res.data)
        # 422 is PUT validation error, means we passed permissions
        assert (res.status_code in (200, 201, 422)) == expected

def get_table(name):
    table_name = dynamodb.gen_table_name('test', name)
    return dynamodb.dynamodb.Table(table_name)

def test_permissions(client, clear_db):
    # We build two artificial units:
    # unit test:
    #  contact: 61412123123
    #  member: 12345
    #  member: 1 - site-admin
    #  member: 2 - unit-admin
    #  member: 3 - contact-maintainer
    #  member: 4 - none
    #  member: 5 - unit-admin, contact-maintainer
    # unit other:
    #  contact: 61400000000
    #  member: 666
    dynamodb.populate_role('test')
    get_table('unit').put_item(Item={
        'name' : 'test',
        'capcode' : 0,
    })
    get_table('unit').put_item(Item={
        'name' : 'other',
        'capcode' : 0,
    })
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : 12345,
        'roles'     : json.dumps(['none'])
    })
    get_table('member').put_item(Item={
        'unit'      : 'other',
        'name'      : 'Other User',
        'member_id' : 666,
        'roles'     : json.dumps(['none'])
    })
    get_table('contact').put_item(Item={
        'unit'         : 'test',
        'phone_number' : '61412123123',
        'member_id'    : 12345
    })
    get_table('contact').put_item(Item={
        'unit'         : 'other',
        'phone_number' : '61400000000',
        'member_id'    : 666
    })

    site_admin_user = 1
    unit_admin_user = 2
    contact_maintainer_user = 3
    none_user = 4
    multiple_user = 5
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : site_admin_user,
        'roles'     : json.dumps(['site-admin'])
    })
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : unit_admin_user,
        'roles'     : json.dumps(['unit-admin'])
    })
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : contact_maintainer_user,
        'roles'     : json.dumps(['contact-maintainer'])
    })
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : none_user,
        'roles'     : json.dumps(['none'])
    })
    get_table('member').put_item(Item={
        'unit'      : 'test',
        'name'      : 'Test User',
        'member_id' : multiple_user,
        'roles'     : json.dumps(['unit-admin', 'contact-maintainer'])
    })


    permission_helper(client, unit_admin_user, [
        ('GET',  '/rest/unit/test',           True),
        ('PUT',  '/rest/unit/test',           True),
        ('GET',  '/rest/unit/test/contacts',  True),
        ('GET',  '/rest/unit/test/pagelog',   True),
        ('GET',  '/rest/unit/test/members',   True),
        ('GET',  '/rest/contact/61412123123', True),
        ('PUT',  '/rest/contact/61412123123', True),
        ('GET',  '/rest/role/unit-admin',     True),
        ('GET',  '/rest/member/12345',        True),
        ('PUT',  '/rest/member/12345',        True),
        ('GET',  '/rest/unit/other',          False),
        ('PUT',  '/rest/unit/other',          False),
        ('GET',  '/rest/unit/other/contacts', False),
        ('GET',  '/rest/unit/other/pagelog',  False),
        ('GET',  '/rest/unit/other/members',  False),
        ('GET',  '/rest/contact/61400000000', False),
        #('PUT',  '/rest/contact/61400000000', False), # TODO
        ('GET',  '/rest/member/666',          False),
        #('PUT',  '/rest/member/666',          False), # TODO
    ])

    permission_helper(client, site_admin_user, [
        ('GET',  '/rest/unit/test',           True),
        ('PUT',  '/rest/unit/test',           True),
        ('GET',  '/rest/unit/test/contacts',  True),
        ('GET',  '/rest/unit/test/pagelog',   True),
        ('GET',  '/rest/unit/test/members',   True),
        ('GET',  '/rest/contact/61412123123', True),
        ('PUT',  '/rest/contact/61412123123', True),
        ('GET',  '/rest/role/unit-admin',     True),
        ('GET',  '/rest/member/12345',        True),
        ('PUT',  '/rest/member/12345',        True),
        ('GET',  '/rest/unit/other',          True),
        ('PUT',  '/rest/unit/other',          True),
        ('GET',  '/rest/unit/other/contacts', True),
        ('GET',  '/rest/unit/other/pagelog',  True),
        ('GET',  '/rest/unit/other/members',  True),
        ('GET',  '/rest/contact/61400000000', True),
        #('PUT',  '/rest/contact/61400000000', True), # TODO
        ('GET',  '/rest/member/666',          True),
        #('PUT',  '/rest/member/666',          True), # TODO
    ])

    permission_helper(client, contact_maintainer_user, [
        ('GET',  '/rest/unit/test',           True),
        ('PUT',  '/rest/unit/test',           False),
        ('GET',  '/rest/unit/test/contacts',  True),
        ('GET',  '/rest/unit/test/pagelog',   True),
        ('GET',  '/rest/unit/test/members',   False),
        ('GET',  '/rest/contact/61412123123', True),
        ('PUT',  '/rest/contact/61412123123', True),
        ('GET',  '/rest/role/unit-admin',     True),
        ('GET',  '/rest/member/12345',        False),
        ('PUT',  '/rest/member/12345',        False),
        ('GET',  '/rest/unit/other',          False),
        ('PUT',  '/rest/unit/other',          False),
        ('GET',  '/rest/unit/other/contacts', False),
        ('GET',  '/rest/unit/other/pagelog',  False),
        ('GET',  '/rest/unit/other/members',  False),
        ('GET',  '/rest/contact/61400000000', False),
        #('PUT',  '/rest/contact/61400000000', False), # TODO
        ('GET',  '/rest/member/666',          False),
        #('PUT',  '/rest/member/666',          False), # TODO
    ])

    permission_helper(client, none_user, [
        ('GET',  '/rest/unit/test',           True),
        ('PUT',  '/rest/unit/test',           False),
        ('GET',  '/rest/unit/test/contacts',  False),
        ('GET',  '/rest/unit/test/pagelog',   True),
        ('GET',  '/rest/unit/test/members',   False),
        ('GET',  '/rest/contact/61412123123', False),
        ('PUT',  '/rest/contact/61412123123', False),
        ('GET',  '/rest/role/unit-admin',     True),
        ('GET',  '/rest/member/12345',        False),
        ('PUT',  '/rest/member/12345',        False),
        ('GET',  '/rest/unit/other',          False),
        ('PUT',  '/rest/unit/other',          False),
        ('GET',  '/rest/unit/other/contacts', False),
        ('GET',  '/rest/unit/other/pagelog',  False),
        ('GET',  '/rest/unit/other/members',  False),
        ('GET',  '/rest/contact/61400000000', False),
        #('PUT',  '/rest/contact/61400000000', False), # TODO
        ('GET',  '/rest/member/666',          False),
        #('PUT',  '/rest/member/666',          False), # TODO
    ])

    permission_helper(client, multiple_user, [
        ('GET',  '/rest/unit/test',           True),
        ('PUT',  '/rest/unit/test',           True),
        ('GET',  '/rest/unit/test/contacts',  True),
        ('GET',  '/rest/unit/test/pagelog',   True),
        ('GET',  '/rest/unit/test/members',   True),
        ('GET',  '/rest/contact/61412123123', True),
        ('PUT',  '/rest/contact/61412123123', True),
        ('GET',  '/rest/role/unit-admin',     True),
        ('GET',  '/rest/member/12345',        True),
        ('PUT',  '/rest/member/12345',        True),
        ('GET',  '/rest/unit/other',          False),
        ('PUT',  '/rest/unit/other',          False),
        ('GET',  '/rest/unit/other/contacts', False),
        ('GET',  '/rest/unit/other/pagelog',  False),
        ('GET',  '/rest/unit/other/members',  False),
        ('GET',  '/rest/contact/61400000000', False),
        #('PUT',  '/rest/contact/61400000000', False), # TODO
        ('GET',  '/rest/member/666',          False),
        #('PUT',  '/rest/member/666',          False), # TODO
    ])
