# Copyright 2019 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
'''
Lambda to associate Tag Options to Service Catalog portoflios
'''
import logging
import json
from botocore.exceptions import ClientError
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)
sc = boto3.client('servicecatalog')


def list_active_tag_options():
    '''
    Return list of all tag options
    '''

    tag_list = list()
    try:
        paginator = sc.get_paginator('list_tag_options')
        page_iterator = paginator.paginate(Filters={'Active': True})
    except ClientError as exe:
        logger.error('Unable to get tag options: %s', str(exe))

    for page in page_iterator:
        tag_list += page['TagOptionDetails']
    return tag_list


def lambda_handler(event, context):
    '''
    Lambda to associate tags to neewly created portfolio.
    '''
    logger.info('EVENT: %s, CONTEXT: %s', event, context)
    port_id = event['detail']['responseElements']['portfolioDetail']['id']
    region = event['region']
    failure_response = dict()
    failure_response['statusCode'] = 404
    failure_response['body'] = json.dumps('Unable to apply TagOptions')

    # Get TagOptions
    tag_options = list_active_tag_options()

    # Associate tag options
    if tag_options:
        for item in tag_options:
            logger.info('Associating TagOption %s to portfolio %s in %s',
                        item, port_id, region)
            try:
                response = sc.associate_tag_option_with_resource(
                    ResourceId=port_id,
                    TagOptionId=item['Id']
                    )
                logger.info('Tag Associated: %s', response)
            except ClientError as exe:
                logger.error('Failed to associate a tag option: %s', str(exe))
                response = dict(failure_response)
                response['message'] = port_id
    else:
        logger.warning('Not Tag Options found to associate in %s', region)
        response = dict(failure_response)
        response['message'] = port_id

    return response
