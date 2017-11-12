[![Build Status](https://travis-ci.org/VICSES/sms-page-rest.svg?branch=master)](https://travis-ci.org/VICSES/sms-page-rest)
[![Coverage Status](https://coveralls.io/repos/github/VICSES/sms-page-rest/badge.svg?branch=master)](https://coveralls.io/github/VICSES/sms-page-rest?branch=master)
[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FVICSES%2Fsms-page-rest.svg?type=shield)](https://app.fossa.io/projects/git%2Bgithub.com%2FVICSES%2Fsms-page-rest?ref=badge_shield)

# Introduction

The project provides a REST interface to sms-page dynamodb tables. It is part of the larger [sms-page](https://github.com/VICSES/sms-page) project.

It is designed to be deployed to an AWS Lambda instance using [zappa](https://github.com/Miserlou/Zappa). 

# Installation

Zappa requires the use of Python 3.6 and a virtual environment.

On a Debian system this can be achieved with the python3.6 package.

```
$ python3.6 -m venv env
$ source env/bin/activate
(env) $ pip3.6 -rrequirements.txt
(env) $ zappa init
(env) $ vim zappa_settings.json
(env) $ zappa deploy prod
```

`zappa_settings.json` must be edited to set the `environment_variables` and ``extra_permissions` as shown in `zappa_settings.example.json`.


# API

* [`GET /rest/unit/:unit`](api.md#get-unit)
* [`PUT /rest/unit/:unit`](api.md#update-unit)
* [`GET /rest/unit/:unit/contacts`](api.md#get-unit-contacts)
* [`GET /rest/unit/:unit/pagelog`](api.md#get-log-of-unit-pages)
* [`GET /rest/unit/:unit/members`](api.md#get-list-of-unit-members)
* [`GET /rest/contact/:phone_number`](api.md#get-contact)
* [`PUT /rest/contact/:phone_number`](api.md#update-contact)
* [`GET /rest/member/:member_id`](api.md#get-member)
* [`PUT /rest/member/:member_id`](api.md#update-member)
* [`GET /rest/role/:name`](api.md#get-role)

# LICENCE

The source code for this project is provided under the terms of the GNU Affero General Public License Version 3 (AGPL-3). A copy of this licence is provided in [LICENCE.md](LICENCE.md).


[![FOSSA Status](https://app.fossa.io/api/projects/git%2Bgithub.com%2FVICSES%2Fsms-page-rest.svg?type=large)](https://app.fossa.io/projects/git%2Bgithub.com%2FVICSES%2Fsms-page-rest?ref=badge_large)