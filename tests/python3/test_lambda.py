import os
import sys
import boto3
import boto
import moto
import botocore
import unittest
import logging
import re
import sure
import botocore.session
from datetime import datetime
from moto import mock_sns_deprecated, mock_sqs_deprecated
from botocore.stub import Stubber
from freezegun import freeze_time
from mock import patch
#from moto import mock_dynamodb2, mock_dynamodb2_deprecated
#from moto.dynamodb2 import dynamodb_backend2
from moto import mock_ec2, mock_ec2_deprecated, mock_route53

myPath = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0,myPath+'/..')

from union_python3 import publish_to_sns, delete_item_from_dynamodb_table, get_subnet_cidr_block, get_item_from_dynamodb_table, list_hosted_zones, get_hosted_zone_properties, is_dns_support_enabled, is_dns_hostnames_enabled, associate_zone, create_reverse_lookup_zone, get_reversed_domain_prefix, reverse_list, get_dhcp_configurations, create_dynamodb_table, list_tables, put_item_in_dynamodb_table, get_dynamodb_table, create_table, change_resource_recordset, create_resource_record, delete_resource_record, get_zone_id, is_valid_hostname, get_dhcp_option_set_id_for_vpc

try:
    import boto.dynamodb2
except ImportError:
    print("This boto version is not supported")

logging.basicConfig(level=logging.DEBUG)

os.environ["AWS_ACCESS_KEY_ID"] = '1111'
os.environ["AWS_SECRET_ACCESS_KEY"] = '2222'

class TestLambda(unittest.TestCase):


    def test_get_subnet_cidr_block(selt):

        mock = moto.mock_ec2()

        mock.start()
        client = boto3.client('ec2', region_name='us-east-1')

        vpc = client.create_vpc(CidrBlock="10.0.0.0/16")
        subnet = client.create_subnet(VpcId=vpc['Vpc']['VpcId'], CidrBlock="10.0.0.0/18")

        results = get_subnet_cidr_block(client, subnet['Subnet']['SubnetId'] )
        assert results == '10.0.0.0/18'
        mock.stop()


    def test_listed_hosted_zones(self):

        mock = moto.mock_route53()
        mock.start()
        client = boto3.client(
            'route53',
            region_name='us-east-1',
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token='123',
        )

        response = client.create_hosted_zone(
            Name='test4',
            VPC={
                'VPCRegion': 'us-east-1',
                'VPCId': 'vpc-43248d39'
            },
            CallerReference='string',
            HostedZoneConfig={
                'Comment': 'string',
                'PrivateZone': True
            }
        )
        hosted_zone_id = response['HostedZone']['Id']

        response = list_hosted_zones(client)
        assert response['HostedZones'][0]['Name'] == 'test4.'
        mock.stop()

    def test_get_hosted_zone_properties(self):


        mock = moto.mock_route53()
        mock.start()
        client = boto3.client(
            'route53',
            region_name='us-east-1',
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token='123',
        )

        response = client.create_hosted_zone(
            Name='string',
            VPC={
                'VPCRegion': 'us-east-1',
                'VPCId': 'vpc-43248d39'
            },
            CallerReference='string',
            HostedZoneConfig={
                'Comment': 'string',
                'PrivateZone': True
            }
        )
        hosted_zone_id = response['HostedZone']['Id']

        response = get_hosted_zone_properties(client, hosted_zone_id)
        assert response['HostedZone']['Id'] == hosted_zone_id
        mock.stop()



    def test_is_dns_support_enabled(self):

        mock = moto.mock_ec2()

        mock.start()
        client = boto3.client('ec2', region_name='us-east-1')
        dhcp_options = client.create_dhcp_options(
            DhcpConfigurations=[
                {
                    'Key': 'example.com',
                    'Values': [
                        '10.0.0.6',
                        '10.0.0.7'
                    ]
                }
            ]
        )
        print('dhcp options: '+str(dhcp_options))

        vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc1: '+str(vpc1))


        response = client.modify_vpc_attribute(
            EnableDnsSupport={
                'Value': True
            },
            VpcId=vpc1['Vpc']['VpcId']
        )

        print('response: '+str(response))

        results = is_dns_support_enabled(client, vpc1['Vpc']['VpcId'])
        print('results: '+str(results))
        assert results == True
        mock.stop()


    def test_is_dns_hostnames_enabled(self):

        mock = moto.mock_ec2()

        mock.start()
        client = boto3.client('ec2', region_name='us-east-1')
        dhcp_options = client.create_dhcp_options(
            DhcpConfigurations=[
                {
                    'Key': 'example.com',
                    'Values': [
                        '10.0.0.6',
                        '10.0.0.7'
                    ]
                }
            ]
        )
        print('dhcp options: '+str(dhcp_options))

        vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc1: '+str(vpc1))


        response = client.modify_vpc_attribute(
            EnableDnsHostnames={
                'Value': True
            },
            VpcId=vpc1['Vpc']['VpcId']
        )

        print('response: '+str(response))

        results = is_dns_hostnames_enabled(client, vpc1['Vpc']['VpcId'])
        print('results: '+str(results))
        assert results == True
        mock.stop()


    @unittest.skip("moto need associate vpc added")
    def test_associate_zone(self):

        mock = moto.mock_route53()
        mock.start()
        client = boto3.client(
            'route53',
            region_name='us-east-1',
            aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
            aws_session_token='123',
        )

        response = client.create_hosted_zone(
            Name='string',
            VPC={
                'VPCRegion': 'us-east-1',
                'VPCId': 'vpc-43248d39'
            },
            CallerReference='string',
            HostedZoneConfig={
                'Comment': 'string',
                'PrivateZone': True
            }
        )

        hosted_zone_id = response['HostedZone']['Id']
        print('response: '+str(response))

        results = associate_zone(client, hosted_zone_id, 'us-east-1', 'vpc-43248d39')

        assert results == 'test'
        mock.stop()

    def test_create_reverse_lookup_zone(self):
        instance = {
            'Reservations' :[
                {
                    'Instances': [
                        {
                            'VpcId': '123'
                        }
                    ]
                }
            ]
        }

        mock = moto.mock_route53()

        mock.start()

        client = boto3.client('route53', region_name='us-east-1')


        response = create_reverse_lookup_zone(client, instance, 'abc.', 'us-east-1')
        assert response['HostedZone']['Name'] == 'abc.in-addr.arpa.'
        mock.stop()



    def test_get_reversed_domain_prefix_16(self):

        results = get_reversed_domain_prefix(16, '10.0.0.1')
        assert results == '10.0.0.'

    def test_get_reversed_domain_prefix_24(self):

        results = get_reversed_domain_prefix(24, '10.0.0.1')
        assert results == '10.0.0.'

    @patch('union_python3.publish_to_sns')
    def test_reverse_list_with_invalid_ip(
            self,
            sns
    ):

        sns.return_value == None
        response = reverse_list('test')

        assert response == None

    def test_reverse_list(self):

        results = reverse_list('172.168.3.7')
        assert results == '7.3.168.172.'


    def test_get_dhcp_configurations(self):

        mock = moto.mock_ec2()

        mock.start()
        client = boto3.client('ec2', region_name='us-east-1')
        dhcp_options = client.create_dhcp_options(
            DhcpConfigurations=[
                {
                    'Key': 'example.com',
                    'Values': [
                        '10.0.0.6',
                        '10.0.0.7'
                    ]
                }
            ]
        )
        print('dhcp options: '+str(dhcp_options))

        vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc1: '+str(vpc1))
        vpc2 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc2: '+str(vpc2))

        vpc3 = client.create_vpc(CidrBlock="10.0.0.0/24")
        print('vpc3: '+str(vpc3))


        client.associate_dhcp_options(DhcpOptionsId=dhcp_options['DhcpOptions']['DhcpOptionsId'], VpcId=vpc1['Vpc']['VpcId'])
        client.associate_dhcp_options(DhcpOptionsId=dhcp_options['DhcpOptions']['DhcpOptionsId'], VpcId=vpc2['Vpc']['VpcId'])


        results = get_dhcp_configurations(client, dhcp_options['DhcpOptions']['DhcpOptionsId'] )
        # Returning nothing now because moto needs fixed
        assert results == []
        mock.stop()



    def test_create_dynamodb_table(self):
        mock = moto.mock_dynamodb2()

        mock.start()
        client = boto3.client('dynamodb', region_name='us-east-1')

        results = create_dynamodb_table(client, 'DDNS')

        assert results['TableDescription']['TableName'] == 'DDNS'
        mock.stop()


    def test_get_dhcp_option_set_id_for_vpc(self):

        SAMPLE_DOMAIN_NAME = u'example.com'
        SAMPLE_NAME_SERVERS = [u'10.0.0.6', u'10.0.0.7']

        mock = moto.mock_ec2()

        mock.start()
        client = boto3.client('ec2', region_name='us-east-1')

        dhcp_options = client.create_dhcp_options(
            DhcpConfigurations=[
                {
                    'Key': 'example.com',
                    'Values': [
                        '10.0.0.6',
                        '10.0.0.7'
                    ]
                }
            ]
        )
        print('dhcp options: '+str(dhcp_options))

        vpc1 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc1: '+str(vpc1))
        vpc2 = client.create_vpc(CidrBlock="10.0.0.0/16")
        print('vpc2: '+str(vpc2))

        vpc3 = client.create_vpc(CidrBlock="10.0.0.0/24")
        print('vpc3: '+str(vpc3))


        client.associate_dhcp_options(DhcpOptionsId=dhcp_options['DhcpOptions']['DhcpOptionsId'], VpcId=vpc1['Vpc']['VpcId'])
        client.associate_dhcp_options(DhcpOptionsId=dhcp_options['DhcpOptions']['DhcpOptionsId'], VpcId=vpc2['Vpc']['VpcId'])

        #vpcs = client.describe_vpcs(Filters=[{'Name': 'dhcp-options-id', 'Values': [dhcp_options['DhcpOptions']['DhcpOptionsId']]}])

        results = get_dhcp_option_set_id_for_vpc(client, vpc1['Vpc']['VpcId'])

        assert results == dhcp_options['DhcpOptions']['DhcpOptionsId']

        mock.stop()

    def test_is_invalid_hostname(self):
        results = is_valid_hostname( None)
        assert results == False

    def test_is_valid_hostname(self):
        results = is_valid_hostname( 'test')
        assert results == True

    def test_get_zone_id(self):

        mock = moto.mock_route53()

        mock.start()

        client = boto3.client('route53', region_name='us-east-1')
        client.create_hosted_zone(
            Name="db.",
            CallerReference=str(hash('foo')),
            HostedZoneConfig=dict(
                PrivateZone=True,
                Comment="db",
            )
        )

        zones = client.list_hosted_zones_by_name(DNSName="db.")

        hosted_zone_id = zones["HostedZones"][0]["Id"]
        # Create A Record.
        a_record_endpoint_payload = {
            'Comment': 'Create A record prod.redis.db',
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'prod.redis.db.',
                        'Type': 'A',
                        'TTL': 10,
                        'ResourceRecords': [{
                            'Value': '127.0.0.1'
                        }]
                    }
                }
            ]
        }
        client.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload)

        results = get_zone_id( client, 'db.')
        assert len(results) == 15
        mock.stop()


    def test_delete_resource_record(self):

        mock = moto.mock_route53()

        mock.start()

        client = boto3.client('route53', region_name='us-east-1')
        client.create_hosted_zone(
            Name="db.",
            CallerReference=str(hash('foo')),
            HostedZoneConfig=dict(
                PrivateZone=True,
                Comment="db",
            )
        )

        zones = client.list_hosted_zones_by_name(DNSName="db.")

        hosted_zone_id = zones["HostedZones"][0]["Id"]
        # Create A Record.
        a_record_endpoint_payload = {
            'Comment': 'Create A record prod.redis.db',
            'Changes': [
                {
                    'Action': 'CREATE',
                    'ResourceRecordSet': {
                        'Name': 'prod.redis.db.',
                        'Type': 'A',
                        'TTL': 10,
                        'ResourceRecords': [{
                            'Value': '127.0.0.1'
                        }]
                    }
                }
            ]
        }
        client.change_resource_record_sets(HostedZoneId=hosted_zone_id, ChangeBatch=a_record_endpoint_payload)


        results = delete_resource_record( client, hosted_zone_id,'prod','redis.db.','A','127.0.0.1')
        assert results['ChangeInfo']['Status'] == 'INSYNC'
        mock.stop()


    def test_create_resource_record(self):

        mock = moto.mock_route53()

        mock.start()

        client = boto3.client('route53', region_name='us-east-1')
        client.create_hosted_zone(
            Name="db.",
            CallerReference=str(hash('foo')),
            HostedZoneConfig=dict(
                PrivateZone=True,
                Comment="db",
            )
        )

        zones = client.list_hosted_zones_by_name(DNSName="db.")

        hosted_zone_id = zones["HostedZones"][0]["Id"]

        results = create_resource_record( client, hosted_zone_id,'prod','redis.db.','A','127.0.0.1')
        assert results['ChangeInfo']['Status'] == 'INSYNC'
        mock.stop()


    def test_change_resource_recordset(self):

        mock = moto.mock_route53()

        mock.start()

        client = boto3.client('route53', region_name='us-east-1')
        client.create_hosted_zone(
            Name="db.",
            CallerReference=str(hash('foo')),
            HostedZoneConfig=dict(
                PrivateZone=True,
                Comment="db",
            )
        )

        zones = client.list_hosted_zones_by_name(DNSName="db.")

        hosted_zone_id = zones["HostedZones"][0]["Id"]

        results = change_resource_recordset( client, hosted_zone_id,'prod','redis.db.','A','127.0.0.1')
        assert results['ChangeInfo']['Status'] == 'INSYNC'
        mock.stop()


    def test_create_table(self):

        mock = moto.mock_dynamodb2()
        mock.start()

        client = boto3.client("dynamodb")


        results = create_table(client, 'DDNS')
        assert results == True
        mock.stop()


    def test_get_dynamodb_table(self):

        mock = moto.mock_dynamodb2()
        mock.start()

        client = boto3.client("dynamodb")
        client.create_table(TableName="DDNS"
                            , KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}]
                            , AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}]
                            , ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1})

        results = get_dynamodb_table(client, 'DDNS')
        assert results['Table']['TableName'] == 'DDNS'
        mock.stop()


    def test_list_tables(self):

        dynamodb_client = botocore.session.get_session().create_client('dynamodb','us-east-1')
        dynamodb_client_stubber = Stubber(dynamodb_client)


        response = {
            'TableNames': [
                'DDNS',
            ],
            'LastEvaluatedTableName': 'DDNS'
        }

        expected_params = {}

        dynamodb_client_stubber.add_response('list_tables', response, expected_params)

        with dynamodb_client_stubber:
            results = list_tables(dynamodb_client)
            assert results['TableNames'][0]== 'DDNS'


    def test_put_item_in_dynamodb_table(self):

        dynamodb_client = botocore.session.get_session().create_client('dynamodb','us-east-1')
        dynamodb_client_stubber = Stubber(dynamodb_client)


        response = {
            'Attributes': {
                'InstanceId': {
                    'S': '123',
                    'NULL': True,
                    'BOOL': True
                },
                'InstanceAttributes': {
                    'S': '123',
                    'NULL': True,
                    'BOOL': True
                }
            },
            'ConsumedCapacity': {
                'TableName': 'string',
                'CapacityUnits': 123.0,
                'ReadCapacityUnits': 123.0,
                'WriteCapacityUnits': 123.0,
                'Table': {
                    'ReadCapacityUnits': 123.0,
                    'WriteCapacityUnits': 123.0,
                    'CapacityUnits': 123.0
                },
                'LocalSecondaryIndexes': {
                    'string': {
                        'ReadCapacityUnits': 123.0,
                        'WriteCapacityUnits': 123.0,
                        'CapacityUnits': 123.0
                    }
                },
                'GlobalSecondaryIndexes': {
                    'string': {
                        'ReadCapacityUnits': 123.0,
                        'WriteCapacityUnits': 123.0,
                        'CapacityUnits': 123.0
                    }
                }
            },
            'ItemCollectionMetrics': {
                'ItemCollectionKey': {
                    'string': {
                        'S': 'string',
                        'N': 'string',
                        'B': b'bytes',
                        'SS': [
                            'string',
                        ],
                        'NS': [
                            'string',
                        ],
                        'BS': [
                            b'bytes',
                        ],
                        'M': {
                            'string': {}
                        },
                        'L': [
                            {},
                        ],
                        'NULL': True,
                        'BOOL': True
                    }
                },
                'SizeEstimateRangeGB': [
                    123.0,
                ]
            }
        }

        expected_params = {
            'TableName': 'DDNS',
            'Item': {
                'InstanceId': {'S':'123'},
                'InstanceAttributes': {'S':'123'}
            }
        }

        dynamodb_client_stubber.add_response('put_item', response, expected_params)

        with dynamodb_client_stubber:
            results =  put_item_in_dynamodb_table(dynamodb_client, 'DDNS', '123','123')
            assert results == response

    def test_get_item_from_dynamodb_table(self):

        mock = moto.mock_dynamodb2()
        mock.start()

        client = boto3.client('dynamodb',
                            region_name='us-west-2',
                            aws_access_key_id="ak",
                            aws_secret_access_key="sk")

        results = create_table(client, 'DDNS')
        print('results: '+str(results))
        results = put_item_in_dynamodb_table(client, 'DDNS', '123', '123')
        print('results: '+str(results))


        results = get_item_from_dynamodb_table(client, 'DDNS', '123')
        print('results: '+str(results))
        assert results == 123

        mock.stop()


    def test_delete_item_from_dynamodb_table(self):

        mock = moto.mock_dynamodb2()
        mock.start()

        client = boto3.client('dynamodb',
                            region_name='us-east-1',
                            aws_access_key_id="ak",
                            aws_secret_access_key="sk")

        results = create_table(client, 'DDNS')
        print('results: '+str(results))
        results = put_item_in_dynamodb_table(client, 'DDNS', '123', '123')
        print('results: '+str(results))


        results = get_item_from_dynamodb_table(client, 'DDNS', '123')
        print('results: '+str(results))
        assert results == 123

        results = delete_item_from_dynamodb_table(client, 'DDNS', '123')
        print('results: '+str(results))

        results = get_item_from_dynamodb_table(client, 'DDNS', '123')
        print('results: ' + str(results))
        assert results == None

        mock.stop()

    @unittest.skip("moto needs TopicArn added to publish")
    @mock_sqs_deprecated
    @mock_sns_deprecated
    def test_publish_to_sns(self):

        MESSAGE_FROM_SQS_TEMPLATE = '{\n  "Message": "%s",\n  "MessageId": "%s"\n}'

        conn = boto.connect_sns()
        conn.create_topic("some-topic")
        topics_json = conn.get_all_topics()
        topic_arn = topics_json["ListTopicsResponse"][
            "ListTopicsResult"]["Topics"][0]['TopicArn']

        sqs_conn = boto.connect_sqs()
        sqs_conn.create_queue("test-queue")

        conn.subscribe(topic_arn, "sqs",
                       "arn:aws:sqs:us-east-1:123456789012:test-queue")

        message_to_publish = 'my message'
        subject_to_publish = "test subject"
        with freeze_time("2015-01-01 12:00:00"):
            published_message = publish_to_sns(conn, '123456789012', 'us-east-1', message_to_publish)


        published_message_id = published_message['MessageId']

        queue = sqs_conn.get_queue("test-queue")
        message = queue.read(1)
        expected = MESSAGE_FROM_SQS_TEMPLATE % (
        message_to_publish, published_message_id, subject_to_publish, 'us-east-1')
        acquired_message = re.sub("\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", '2015-01-01T12:00:00.000Z',
                                  message.get_body())
        acquired_message.should.equal(expected)

