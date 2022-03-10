import os
import json
import boto3
import logging

_logger = logging.getLogger()
_logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

client = boto3.client('lambda')


def skip_changes(changed_property, ignore_aws_resource_list):
    '''
    skip_changes()
    Description:
        Function returns True if changing property should be ignored.

    Attributes:
    - changed_property:dict
        Description: The changing property event. 
        Example:
        ---
        {
            'previousValue': {
                'resourceId': 'vol-xxxxxxxxxxxxxxxxx',
                'resourceName': null,
                'resourceType': 'AWS::EC2::Volume',
                'name': 'Is attached to Volume'
            },
            'updatedValue': null,
            'changeType': 'DELETE'
        }
        ---

    - ignore_aws_resource_list:list
        Description: The list of AWS resources to skip
        ---
        ['AWS::EC2::Volume']
        ---
    '''
    status_skipping = False

    if changed_property['changeType'] == 'DELETE':
        aws_resource_current = changed_property['previousValue']['resourceType']
        if aws_resource_current in ignore_aws_resource_list:
            _logger.info(
                f'The {aws_resource_current} deleting was marked as spam. Skipped.')
            status_skipping = True

    elif changed_property['changeType'] == 'UPDATE':
        aws_resource_current = changed_property['previousValue']['resourceType']
        if aws_resource_current in ignore_aws_resource_list:
            _logger.info(
                f'The {aws_resource_current} updating was marked as spam. Skipped.')
            status_skipping = True

    elif changed_property['changeType'] == 'CREATE':
        aws_resource_current = changed_property['updatedValue']['resourceType']
        if aws_resource_current in ignore_aws_resource_list:
            _logger.info(
                f'The {aws_resource_current} creating was marked as spam. Skipped.')
            status_skipping = True
    else:
        status_skipping = False

    return status_skipping

def lambda_handler(event, context):
    _logger.info(event)
    status_code = ''
    trigger_lambda = False

    if not event['invokingEvent']:
        _logger.info('No "invokingEvent". Skip execution.')
    else:
        diff = json.loads(event['invokingEvent'])
        if diff['configurationItemDiff']:
            for k, v in diff['configurationItemDiff']['changedProperties'].items():
                if 'BlockDeviceMappings' in k:
                    _logger.info(
                        f'The EBS attaching was marked as spam. Skipped.')
                elif 'Relationships' in k:
                    trigger_lambda = not skip_changes(v, ["AWS::EC2::Volume"])
                else:
                    trigger_lambda = True
            if trigger_lambda:
                _logger.info(
                    f'Triggering {os.environ.get("INVENTORY_FUNCTION_NAME")} lambda')
                response = client.invoke(
                    FunctionName=os.environ.get('INVENTORY_FUNCTION_NAME'),
                    InvocationType='Event',
                    ClientContext='string',
                    Payload=json.dumps({"TriggeredBy": context.function_name}),
                )

                status_code = response['StatusCode']

        else:
            _logger.info('No "configurationItemDiff". Skip execution.')

    return {
        'statusCode': status_code,
        'body': json.dumps('Parsing was done.')
    }
