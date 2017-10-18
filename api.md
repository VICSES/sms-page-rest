# Contents

* [`GET /rest/unit/:unit`](#get-unit)
* [`PUT /rest/unit/:unit`](#update-unit)
* [`GET /rest/unit/:unit/contacts`](#get-unit-contacts)
* [`GET /rest/unit/:unit/pagelog`](#get-log-of-unit-pages)
* [`GET /rest/unit/:unit/members`](#get-list-of-unit-members)
* [`GET /rest/contact/:phone_number`](#get-contact)
* [`PUT /rest/contact/:phone_number`](#update-contact)
* [`GET /rest/member/:member_id`](#get-member)
* [`PUT /rest/member/:member_id`](#update-member)
* [`GET /rest/role/:name`](#get-role)

# Get unit

Used to get details on the specified unit.

**URL**: `/rest/unit/:unit`

**Method**: `GET`

**Permissions required**: `own unit or unit-read`

**URL Params**: `unit = string, valid unit name`

## Success Response

**Code**: `200 OK`

**Content example**
```json
{
	"name": "Bellarine",
	"capcode": 10102
}
```

## Error Response

**Condition**: If unit could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Update unit

Used to edit or create the specified unit.

**URL**: `/rest/unit/:unit`

**Method**: `PUT`

**Permissions required**: `(own unit and myunit-unit-write) or unit-write`

**URL Params**: `unit = string, valid unit name`

**Data constraints**
```json
{
	"capcode": integer, required
}
```

**Data example**
```json
{
	"capcode": 10102
}
```

## Success Response

**Code**: `200 OK`  
**Code**: `201 Created`

**Content example**
```json
{
	"name": "Bellarine",
	"capcode": 10102
}
```

## Error Response

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`

**Condition**: If data did not validate  
**Code**: `422 Unprocessable Entity`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get unit contacts

Used to get the contacts for a given unit.

**URL**: `/rest/unit/:unit/contacts`

**Method**: `GET`

**Permissions required**: `(own unit and myunit-contact-read) or contact-read`

**URL Params**: `unit = string, valid unit name`

## Success Response

**Code**: `200 OK`

**Content example**
```json
[
	{
		"phone_number": "61402123123",
		"unit": "Bellarine",
		"member_id": 612
	},
	{
		"phone_number": "61567321321",
		"unit": "Bellarine",
		"member_id": 787
	}
}
```

## Error Response

**Condition**: If unit could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get log of unit pages

Used to get the log of pages for a given unit.

**URL**: `/rest/unit/:unit/pagelog`

**Method**: `GET`

**Permissions required**: `(own unit and myunit-pagelog-read) or pagelog-read`

**URL Params**: `unit = string, valid unit name`

## Success Response

**Code**: `200 OK`

**Content example**
```json
[
	{
		"unit": "Bellarine",
		"timestamp": 1509703002.2548757,
		"phone_number": "61402123123",
		"body": "S171030602 BELL - ANIMAL INCIDENT - DOG TRAPPED IN A WELL - CLIFTON SPRINGS GOLF CLUB M 456 J5 FRED SMITH 0412123123 [BELL]"
	},
	{
		"unit": "Bellarine",
		"timestamp": 1509703183.9556262,
		"phone_number": "61422321123",
		"body": "Reminder to send through Map & Navigation Course Nominations for 24,25,26 November - Bannockburn [S_W_INFO]"
	}
}
```

## Error Response

**Condition**: If unit could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get list of unit members

Used to get the list of members for a given unit.

**URL**: `/rest/unit/:unit/members`

**Method**: `GET`

**Permissions required**: `(own unit and myunit-member-read) or member-read`

**URL Params**: `unit = string, valid unit name`

## Success Response

**Code**: `200 OK`

**Content example**
```json
[
	{
		"member_id": 60012,
		"name": "John Member",
		"unit": "Bellarine",
		"roles": ["site-admin"]
	},
	{
		"member_id": 67021,
		"name": "Valerie Smith",
		"unit": "Bellarine",
		"roles": ["contact-maintainer"]
	}
}
```

## Error Response

**Condition**: If unit could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get contact

Used to get details on the specified contact.

**URL**: `/rest/contact/:phone_number`

**Method**: `GET`

**Permissions required**: `(own unit and myunit-contact-read) or contact-read`

**URL Params**: `phone_number = string, existing phone number`

## Success Response

**Code**: `200 OK`

**Content example**
```json
{
	"phone_number": "61402123123",
	"unit": "Bellarine",
	"member_id": 612
}
```

## Error Response

**Condition**: If contact could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Update contact

Used to edit or create the specified contact.

**URL**: `/rest/contact/:phone_number`

**Method**: `PUT`

**Permissions required**: `(own unit and myunit-contact-write) or contact-write`

**URL Params**: `phone_number = string, valid international mobile number`

**Data constraints**
```json
{
	"unit": string, existing unit, required,
	"member_id": integer, required
}
```

**Data example**
```json
{
	"unit": "Bellarine",
	"member_id": 612
}
```

## Success Response

**Code**: `200 OK`  
**Code**: `201 Created`

**Content example**
```json
{
	"phone_number": "61402123123",
	"unit": "Bellarine",
	"member_id": 612
}
```

## Error Response

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`

**Condition**: If data did not validate  
**Code**: `422 Unprocessable Entity`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get member

Used to get details on the specified member.

**URL**: `/rest/member/:member_id`

**Method**: `GET`

**Permissions required**: `(own unit and myunit-member-read) or member-read`

**URL Params**: `member_id = integer, existing member id`

## Success Response

**Code**: `200 OK`

**Content example**
```json
{
	"member_id": 60012,
	"name": "Jane Member",
	"unit": "Bellarine",
	"roles": ["site-admin"]
}
```

## Error Response

**Condition**: If member could not be found  
**Code**: `404 Not Found`

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Update member

Used to edit or create the specified member.

**URL**: `/rest/member/:member_id`

**Method**: `PUT`

**Permissions required**: `(own unit and myunit-member-write) or member-write`

**URL Params**: `member_id = integer, existing member id`

**Data constraints**
```json
{
	"name": string, required,
	"unit": string, existing unit, required,
	"roles": json list of strings, existing roles, required
}
```

**Data example**
```json
{
	"name": "Jane Member",
	"unit": "Bellarine",
	"roles": ["site-admin"]
}
```

## Success Response

**Code**: `200 OK`  
**Code**: `201 Created`

**Content example**
```json
{
	"member_id": 60012,
	"name": "Jane Member",
	"unit": "Bellarine",
	"roles": ["site-admin"]
}
```

## Error Response

**Condition**: If user has insufficient permissions  
**Code**: `403 Forbidden`

**Condition**: If data did not validate  
**Code**: `422 Unprocessable Entity`


* * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * *


# Get role

Used to get details on the specified role.

**URL**: `/rest/role/:name`

**Method**: `GET`

**Permissions required**: None

**URL Params**: `name = string`

## Success Response

**Code**: `200 OK`

**Content example**
```json
{
	"name": "site-admin",
	"permissions": ["pagelog-read", "member-write"]
}
```

## Error Response

**Condition**: If role could not be found  
**Code**: `404 Not Found`

