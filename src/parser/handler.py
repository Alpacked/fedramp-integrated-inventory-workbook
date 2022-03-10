import os
import json
import boto3
import logging

_logger = logging.getLogger()
_logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))

client = boto3.client('lambda')


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
                    try:
                        if v['previousValue']['resourceType'] == "AWS::EC2::Volume":
                            _logger.info(f'The EBS updating was marked as spam. Skip execution.')
                    except TypeError:
                        pass
                    try:
                        if v['updatedValue']['resourceType'] == "AWS::EC2::Volume":
                            _logger.info(f'The EBS updating was marked as spam. Skip execution.')
                    except TypeError:
                        pass
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
