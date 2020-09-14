import os
import sys
import boto3
import boto
import moto
import botocore
import unittest
import logging
import botocore.session
from datetime import datetime

from botocore.stub import Stubber
from mock import patch
#from moto import mock_dynamodb2, mock_dynamodb2_deprecated
#from moto.dynamodb2 import dynamodb_backend2
from moto import mock_ec2, mock_ec2_deprecated, mock_route53

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,myPath+'/..')

from union_python3 import lambda_handler, delete_item_from_dynamodb_table, get_subnet_cidr_block, get_item_from_dynamodb_table, list_hosted_zones, get_hosted_zone_properties, is_dns_support_enabled, is_dns_hostnames_enabled, associate_zone, create_reverse_lookup_zone, get_reversed_domain_prefix, reverse_list, get_dhcp_configurations, create_dynamodb_table, list_tables, put_item_in_dynamodb_table, get_dynamodb_table, create_table, change_resource_recordset, create_resource_record, delete_resource_record, get_zone_id, is_valid_hostname, get_dhcp_option_set_id_for_vpc

try:
    import boto.dynamodb2
except ImportError:
    print("This boto version is not supported")

logging.basicConfig(level=logging.DEBUG)

os.environ["AWS_ACCESS_KEY_ID"] = '1111'
os.environ["AWS_SECRET_ACCESS_KEY"] = '2222'
os.environ["USING_CNAMES"] = 'True'

class TestLambda(unittest.TestCase):

    @mock_route53
    @mock_ec2_deprecated
    @patch('union_python3.get_dhcp_option_set_id_for_vpc')
    @patch('union_python3.get_hosted_zone_properties')
    @patch('union_python3.is_dns_support_enabled')
    @patch('union_python3.is_dns_hostnames_enabled')
    @patch('union_python3.get_subnet_cidr_block')
    @patch('union_python3.get_dhcp_configurations')
    @patch('union_python3.change_resource_recordset')
    @patch('union_python3.list_hosted_zones')
    @patch('union_python3.get_instances')
    def test_lambda_handler_private_subnet_with_cname_and_zone_tags(
            self,
            instance_info,
            hosted_zones,
            change_resource_recordset,
            dhcp_configurations,
            get_subnet_cidr,
            hostnames_enabled,
            dnssupport_enabled,
            get_hostedzone_properties,
            dhcp_option_set_id_for_vpc
        ):

        dhcp_option_set_id_for_vpc.return_value='dopt-52a0ea29'

        mock = moto.mock_dynamodb2()
        mock.start()

        client = boto3.client("dynamodb")
        client.create_table(
            TableName="DDNS",
            AttributeDefinitions=[
                {
                    "AttributeName": "InstanceId",
                    "AttributeType": "S"
                }
            ],
            KeySchema=[
                {
                    "AttributeName": "InstanceId",
                    "KeyType": "HASH"
                }
            ],

            ProvisionedThroughput={
                "ReadCapacityUnits": 1,
                "WriteCapacityUnits": 1
            }
        )

        get_hostedzone_properties.return_value =  {

            'HostedZone': {
                'Id': '/hostedzone/Z2705FFK9RBG8N',
                'Name': 'ue1.high.test.com.',
                'CallerReference': 'RISWorkflow-RD:7c9d0012-6791-4dca-b438-0b820efca179',
                'Config': {
                    'Comment': 'test',
                    'PrivateZone': True
                },
                'ResourceRecordSetCount': 14
            },
            'DelegationSet': {
                'NameServers': [
                    'ns-1667.awsdns-16.co.uk',
                    'ns-1140.awsdns-14.org',
                    'ns-44.awsdns-05.com',
                    'ns-530.awsdns-02.net'
                ]
            },
            'VPCs': [
                {
                    'VPCRegion': 'us-east-1',
                    'VPCId': 'vpc-43248d39'
                },
            ],
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'omitted'
            }
        }

        dnssupport_enabled.return_value = True
        hostnames_enabled.return_value = True
        get_subnet_cidr.return_value = '172.31.80.0/24'


        dhcp_configurations.return_value = [
            'ue1.high.test.com.',
            'AmazonProvidedDNS.'
        ]

        change_resource_recordset.return_value = {
            'ChangeInfo': {
                'Id': 'string',
                'Status': 'INSYNC',
                'SubmittedAt': datetime(2015, 1, 1),
                'Comment': 'string'
            }
        }


        instance_info.return_value = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'omitted'
            },
            'Reservations': [
                {
                    'Instances': [
                        {
                            'AmiLaunchIndex': 123,
                            'ImageId': 'string',
                            'InstanceId': 'i-00deb668716374ec7',
                            'InstanceType': 't1.micro',
                            'KernelId': '',
                            'KeyName': 'string',
                            'LaunchTime': datetime(2015, 1, 1),
                            'Monitoring': {
                                'State': 'enabled'
                            },
                            'PrivateDnsName': 'ip-172-31-90-228.ec2.internal',
                            'PrivateIpAddress': '172.31.90.228',
                            'StateTransitionReason': 'string',
                            'SubnetId': 'subnet-24fe650a',
                            'VpcId': 'vpc-43248d39',
                            'Architecture': 'x86_64',
                            'Tags': [
                                {
                                    'Key': 'ZONE',
                                    'Value': 'ue1.high.test.com.'
                                }
                            ]
                        },
                    ],
                    'OwnerId': 'string',
                    'RequesterId': 'string',
                    'ReservationId': 'string'
                }
            ]
        }

        hosted_zones.return_value = {
            'ResponseMetadata': {
                'HTTPStatusCode': 200,
                'RequestId': 'omitted'
            },
            'HostedZones': [
                {
                    'Id': '/hostedzone/Z2705FFK9RBG8N',
                    'Name': 'ue1.high.test.com.',
                    'CallerReference': 'RISWorkflow-RD:7c9d0012-6791-4dca-b438-0b820efca179',
                    'Config': {
                        'Comment': 'string',
                        'PrivateZone': True
                    },
                    'ResourceRecordSetCount': 123,
                    'LinkedService': {
                        'ServicePrincipal': 'string',
                        'Description': 'string'
                    }
                },
                {
                    'Id': '/hostedzone/Z2705FFK9RBG8O',
                    'Name': '90.31.172.in-addr.arpa.',
                    'CallerReference': 'RISWorkflow-RD:7c9d0012-6791-4dca-b438-0b820efca179',
                    'Config': {
                        'Comment': 'string',
                        'PrivateZone': True
                    },
                    'ResourceRecordSetCount': 123,
                    'LinkedService': {
                        'ServicePrincipal': 'string',
                        'Description': 'string'
                    }
                }
            ],
            'Marker': 'string',
            'IsTruncated': True,
            'NextMarker': 'string',
            'MaxItems': 'string'
        }



        event = {
            'region': 'us-east-1',
            'account': '123456789012',
            'detail': {
                'state': 'running',
                'instance-id': 'i-00deb668716374ec7'
            }
        }


        response = lambda_handler(event, 'context', dynamodb_client=client)
        assert response[0] == 'Successfully created recordsets'
        assert response[1] == 'Created A record in zone id: Z2705FFK9RBG8N for hosted zone ip-172-31-90-228.ue1.high.test.com. with value: 172.31.90.228'
        assert response[2] == 'Created PTR record in zone id: Z2705FFK9RBG8O for hosted zone 228.90.31.172.in-addr.arpa with value: ip-172-31-90-228.ec2.internal'
        assert response[3] == 'Created A record in zone id: Z2705FFK9RBG8N for hosted zone ip-172-31-90-228.ue1.high.test.com. with value: 172.31.90.228'
        assert response[4] == 'Created PTR record in zone id: Z2705FFK9RBG8O for hosted zone 228.90.31.172.in-addr.arpa with value: ip-172-31-90-228.ec2.internal'


        mock.stop()

