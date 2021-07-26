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
Lambda to create, update, delete tag options to SC portfolios
'''

import logging
from collections import defaultdict
from botocore.exceptions import ClientError
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

sc = boto3.client('servicecatalog')
dydb = boto3.resource('dynamodb')
tbl = dydb.Table('SCTagOptions')


def list_all_tag_options():
    '''
    Return list of all tag options
    '''

    tag_list = list()
    try:
        paginator = sc.get_paginator('list_tag_options')
        page_iterator = paginator.paginate()
    except ClientError as exe:
        logger.error('Unable to get tag options: %s', str(exe))
    for page in page_iterator:
        tag_list += page['TagOptionDetails']
    return tag_list


def list_all_resources_for_tag_option(tag_opt_id):
    '''List all resources associated with a tag option'''

    tag_list = list()
    try:
        paginator = sc.get_paginator('list_resources_for_tag_option')
        page_iterator = paginator.paginate(TagOptionId=tag_opt_id)
    except ClientError as exe:
        logger.error('Unable to get resource list: %s', str(exe))
    for page in page_iterator:
        tag_list += page['ResourceDetails']
    return tag_list


def list_all_portfolio_ids():
    '''Return list of portfolio ids'''

    portfolio_list = list()
    id_list = list()

    try:
        paginator = sc.get_paginator('list_portfolios')
        page_iterator = paginator.paginate()
    except ClientError as exe:
        logger.error('Unable to get list of portfolios: %s', str(exe))

    for page in page_iterator:
        portfolio_list += page['PortfolioDetails']

    for item in portfolio_list:
        id_list.append(item['Id'])

    return id_list


def get_sc_tags():
    '''
    Return list of all tag options
    '''

    tag_on_sc = defaultdict(list)
    try:
        for tag in list_all_tag_options():
            if tag['Active']:
                tag_on_sc[tag['Key']].append(tag['Value'])
    except ClientError as exe:
        logger.error('Exception occurred: %s', str(exe))
    return tag_on_sc


def update_sc_tagoptions(new_tags, action):
    '''
    Add / Remove new tags in Service Catalog
    '''

    sc_dict = get_sc_tags()
    if action in ['INSERT', 'MODIFY']:
        for key in new_tags.keys():
            if key not in sc_dict.keys():
                logger.info('Adding new tags: %s', new_tags)
                add_new_tags(new_tags, action)
            else:
                if all(e in sc_dict[key] for e in new_tags[key]):
                    logger.info('Tag combination %s exists. Skipping',
                                new_tags[key])
                else:
                    logger.info('Adding New Tags: %s', new_tags)
                    add_new_tags(new_tags, action)

    elif action == 'REMOVE':
        for key in new_tags.keys():
            if key in sc_dict.keys():
                if all(e in sc_dict[key] for e in new_tags[key]):
                    logger.info('Removing New Tags: %s', new_tags)
                    delete_new_tags(new_tags)


def get_tag_id(new_tags):
    '''
    Return Tag Id of a given tag
    '''

    tag_options_list = list_all_tag_options()

    for key in new_tags.keys():
        for item in tag_options_list:
            if key == item['Key'] and new_tags[key][0] == item['Value']:
                return item['Id']


def create_tag_option(new_tags):
    '''
    Create a Tag Option
    '''

    for key in new_tags.keys():
        logger.info('Creating Tag Option: %s.%s', key, new_tags[key][0])
        try:
            sc.create_tag_option(Key=key, Value=new_tags[key][0])
        except ClientError as exe:
            logger.error('Unable to create tag options: %s', str(exe))
        tag_opt_id = get_tag_id(new_tags)
        logger.info('TagOptionId: %s', tag_opt_id)
        associate_tags(tag_opt_id)


def add_new_tags(new_tags, action):
    '''
    Create / Update Tag Options
    '''

    if action == 'INSERT':
        create_tag_option(new_tags)
    else:
        for key in new_tags.keys():
            logger.info('Updating Tag Option: %s.%s', key, new_tags[key][0])
            try:
                sc.update_tag_option(Key=key, Value=new_tags[key][0])
            except ClientError as exe:
                logger.error('Unable to update tag option: %s', str(exe))


def delete_new_tags(new_tags):
    '''
    Delete Tag Options
    '''

    tag_opt_id = get_tag_id(new_tags)
    resource_list = list_associates_for_tag(tag_opt_id)
    disassociate_tags(resource_list, tag_opt_id)
    logger.info('Deleting Tag Option: %s', tag_opt_id)
    try:
        sc.delete_tag_option(Id=tag_opt_id)
    except ClientError as exe:
        logger.error('Unable to delete tag options: %s', str(exe))


def list_associates_for_tag(tag_opt_id):
    '''
    return all associated resources for a given tag
    '''

    resource_list = list()

    for item in list_all_resources_for_tag_option(tag_opt_id):
        resource_list.append(item['Id'])

    return resource_list


def disassociate_tags(resource_list, tag_opt_id):
    '''
    Disassociate a tag from all SC portfolios
    '''

    for item in resource_list:
        logger.info('Disassociating %s from %s', tag_opt_id, item)
        try:
            sc.disassociate_tag_option_from_resource(
                ResourceId=item, TagOptionId=tag_opt_id
                )
        except ClientError as exe:
            logger.error('Unable to disassociate a tag: %s', str(exe))


def associate_tags(tag_opt_id):
    '''
    Associate a tag all SC portfolios
    '''

    resource_list = list_all_portfolio_ids()
    logger.info('ResourceList: %s', resource_list)
    for item in resource_list:
        logger.info('Associating %s from %s', tag_opt_id, item)
        try:
            sc.associate_tag_option_with_resource(
                ResourceId=item, TagOptionId=tag_opt_id
                )
        except ClientError as exe:
            logger.error('Unable to associate a tag: %s', str(exe))


def lambda_handler(event, context):
    '''
    lambda handler to update SC tags
    '''
    new_tags = dict()
    logger.info('EVENT: %s, CONTEXT: %s', event, context)

    for record in event['Records']:
        key = record['dynamodb']['Keys']['Key']['S']
        value = record['dynamodb']['Keys']['Value']['S']
        action = record['eventName']
        new_tags[key] = [value]
        logger.info('Changing: %s', new_tags)
        update_sc_tagoptions(new_tags, action)

    return event
