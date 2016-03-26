#Building a Dynamic DNS for Route 53 using CloudWatch Events and Lambda

Dynamic registration of resource records is useful when you have instances that are not behind a load balancer that you would like address by a host name and domain suffix of your choosing rather than the default <region>.compute.internal or ec2.internal. 

In this post, we explore how you can use [CloudWatch Events](https://aws.amazon.com/cloudwatch) and Lambda to create a Dynamic DNS for Route 53. Besides creating A records, this solution allows you to create alias records for when you want to address a server by a "friendly" or alternate name. Although this is antithetical to treating instances as disposable resources, there are still a lot of shops that find this useful.

With the advent of CloudWatch Events in January 2016, you can now get near real-time information when an AWS resource changes its state, including when instances are launched or terminated.  When you combine this with the power of [Amazon Route 53](https://aws.amazon.com/route53) and [AWS Lambda](https://aws.amazon.com/lambda), you can create a system that closely mimics the behavior of Dynamic DNS.  

For example, when a newly-launched instance changes its state from pending to running, an event can be sent to a Lambda function that creates a resource record in the appropriate Route 53 hosted zone.  Similarly, when instances are stopped or terminated, Lambda can automatically remove resource records from Route 53.  

The example provided in this post works precisely this way.  It uses information from a CloudWatch event to gather information about the instance, such as its public and private DNS name, its public and private IP address, the VPC ID of the VPC that the instance was launch in, its tags, and so on.  It then uses this information to create A, PTR, and CNAME records in the appropriate Route 53 public or private hosted zone.  The solution persists data about the instances in an [Amazon DynamoDB](https://aws.amazon.com/dynamodb) table so it can remove resource records when instances are stopped or terminated. 

##Hosted zones

Route 53 offers the convenience of domain name services without having to build a globally distributed highly reliable DNS infrastructure.  It allows instances within your VPC to resolve the names of resources that run within your AWS environment. It also lets clients on the Internet resolve names of your public-facing resources.  This is accomplished by querying resource record sets that reside within a Route 53 public or private hosted zone.   

A private hosted zone is basically a container that holds information about how you want to route traffic for a domain and its subdomains within one or more VPC whereas a public hosted zone is a container that holds information about how you want to route traffic from the Internet.

##VPC DNS or private hosted zones?

Admittedly, you can use VPC DNS for internal name resolution instead of Route 53 private hosted zones.  Although it doesn’t dynamically create resource records, VPC DNS will provide name resolution for all the hosts within a VPC’s CIDR range.  

Unless you create a DHCP option set with a custom domain name and disable hostnames at the VPC, you can’t change the domain suffix; all instances are either assigned the ec2.internal or <region>.compute.internal domain suffix.  You can’t create aliases or other resource record types with VPC DNS either.  

Private hosted zones help you overcome these challenges by allowing you to create different resource record types with a custom domain suffix.  Moreover, with Route 53 you can create a subdomain for your current DNS namespace or you can migrate an existing subdomain to Route 53.  By using these options, you can create a contiguous DNS namespace between your on-premises environment and AWS.  

Route 53 also has support for split horizon DNS where a different address for a resource record is returned for the same record depending on the origin of the request. This is particularly useful if you want to maintain internal and external versions of the same website or application (for example, for testing changes before you make them public). So while VPC DNS can provide basic name resolution for your VPC, Route 53 private hosted zones offer richer functionality by comparison.  It also has a programmable API that can be used to automate the creation/removal of records sets and hosted zones which we’re going leverage later in this post. 

Route 53 doesn't offer support for dynamic registration of resource record sets for public or private hosted zones.  This can pose challenges when an automatic scaling event occurs and the instances are not behind a load balancer.  A common workaround is to use an automation framework like Chef, Puppet, Ansible, or Salt to create resource records, or by adding instance user data to the launch profile of the Auto Scaling group.  The drawbacks to these approaches is that:

1. automation frameworks typically require you to manage additional infrastructure.
2. instance user data doesn't handle the removal of resource records when the instance is terminated.

This was the motivation for creating a serverless architecture that dynamically creates and removes resource records from Route 53 as EC2 instances are created and destroyed.

##DDNS/Lambda example

Make sure that you have the latest version of the AWS CLI installed locally.   For more information, see [Getting Set Up with the AWS Command Line Interface](http://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-set-up.html).

For this example, create a new VPC configured with a private and public subnet, using [Scenario 2: VPC with Public and Private Subnets (NAT)](http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_Scenario2.html) from the Amazon VPC User Guide.  Ensure that the VPC has the DNS resolution and DNS hostnames options set to yes.

After the VPC is created, you can proceed to the next steps.

#####Step 1 – Create an IAM role for the Lambda function

In this step, you use the AWS Command Line Interface (AWS CLI) to create the Identity and Access Management (IAM) role that the Lambda function assumes when the function is invoked.  You need to create an IAM policy with the required permissions and then attach this policy to the role. 

1) Download the **ddns-policy.json** and **ddns-trust.json** files from the [AWS Labs GitHub repo](https://github.com/awslabs/aws-lambda-ddns-function).  

_ddns-policy.json_

The policy includes **ec2:Describe permission**, required for the function to obtain the EC2 instance’s attributes, including the private IP address, public IP address, and DNS hostname.   The policy also includes DynamoDB and Route 53 full access, required for the function to create the DynamoDB table and to update the Route 53 DNS records.  The policy also allows the function to create log groups and log events.
```JSON
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "ec2:Describe*",
    "Resource": "*"
  }, {
    "Effect": "Allow",
    "Action": [
      "dynamodb:*"
    ],
    "Resource": "*"
  }, {
    "Effect": "Allow",
    "Action": [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:PutLogEvents"
    ],
    "Resource": "*"
  }, {
    "Effect": "Allow",
    "Action": [
      "route53:*"
    ],
    "Resource": [
      "*"
    ]
  }]
}
```
_ddns-trust.json_

The **ddns-trust.json** file contains the trust policy that grants the Lambda service permission to assume the role.
```JSON
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "",
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```
2) Create the policy using the policy document in the **ddns-pol.json** file.  You need to replace **<LOCAL PATH>** with your local path to the **ddns-pol.json** file.   The output of the **aws iam create-policy** command includes the Amazon Resource Locator (ARN).  Save the ARN as you need it for future steps.
```
aws iam create-policy --policy-name ddns-lambda-policy --policy-document file://<LOCAL PATH>/ddns-pol.json
```
3) Create the **ddns-lambda-role IAM role** using the trust policy in the **ddns-trust.json** file.  You need to replace **<LOCAL PATH>** with your local path to the **ddns-trust.json** file.  The output of the **aws iam create-role** command includes the ARN associated with the role that you created.  Save this ARN as you need it when you create the Lambda function in the next section.
```
aws iam create-role --role-name ddns-lambda-role --assume-role-policy-document file://<LOCAL PATH>/ddns-trust.json
```
4) Attach the policy to the role.  Use the ARN returned in step 2 for the **--policy-arn** input parameter.
```
aws iam attach-role-policy --role-name ddns-lambda-role --policy-arn <enter-your-policy-arn-here>
```
#####Step 2 – Create the Lambda function

The Lambda function uses modules included in the Python 2.7 Standard Library and the AWS SDK for Python module (boto3), which is preinstalled as part of the Lambda service.  As such, you do not need to create a deployment package for this example.

- The function first checks if the “DDNS” table exists in DynamoDB and creates the table if it does not.  The table is used to keep a record of instances that have been created, along with their attributes.  It is necessary to do this because after an EC2 instance is terminated, its attributes are no longer available, so they must be fetched from the table.

- The function then queries the event data to determine the change in the EC2 state.  If the state is “running”, the function queries the EC2 instance for the data.  If the state is anything else, it retrieves the information from the “DDNS” DynamoDB table.

The function checks to ensure the VPC has the “DNS resolution” and “DNS hostnames” enabled as they are required in order to use Route 53 private hosted zones.  Next, the function checks whether a reverse lookup zone for the instance already exists.  If it does, it checks to see whether the reverse lookup zone is associated with the instance's VPC.  If it isn't, it creates the association.  This association is needed so the VPC uses Route 53 for DNS resolution.

- Next, the function checks the EC2 instance’s tags for the CNAME and ZONE tags.  If the ZONE tag is found, the function creates A and PTR records in the specified zone.  If the CNAME tag is found, the function creates a CNAME record in the specified zone.

Next, the function checks to see whether there's a DHCP option set assigned to the VPC.  If there is, it uses the value of the domain name to create resource records in the appropriate Route 53 private hosted zone.  The function also checks to see whether there's an association between the instance's VPC and the private hosted zone.  If there isn't, it creates it.

- The function deletes the required DNS resource records if the state of the EC2 instance changes to “shutting down” or “stopped”.

Use the AWS CLI to create the Lambda function:

1) Download the **union.py.zip** file from the [AWS Labs GitHub repo](https://github.com/awslabs/aws-lambda-ddns-function).
2) Execute the following command to create the function.  Note that you need to update the command to use the ARN of the role that you created earlier, as well as the local path to the union.py.zip file containing the Python code for the Lambda function.
```
aws lambda create-function --function-name ddns_lambda --runtime python2.7 --role <enter-your-role-arn-here> --handler union.lambda_handler --timeout 30 --zip-file fileb://<LOCAL PATH>/union.py.zip
```
3) The output of the command returns the ARN of the newly-created function.  Save this ARN, as you need it in the next section.

#####Step 3 – Create the CloudWatch Events Rule

In this step, you create the CloudWatch Events rule that triggers the Lambda function whenever CloudWatch detects a change to the state of an EC2 instance.  You configure the rule to fire when any EC2 instance state changes to “running”, “shutting down”, or “stopped”.  Use the **aws events put-rule** command to create the rule and set the Lambda function as the execution target:
```
aws events put-rule --event-pattern "{\"source\":[\"aws.ec2\"],\"detail-type\":[\"EC2 Instance State-change Notification\"],\"detail\":{\"state\":[\"running\",\"shutting-down\",\"stopped\"]}}" --state ENABLED --name ec2_lambda_ddns_rule
```
The output of the command returns the ARN to the newly created CloudWatch Events rule, named **ec2\_lambda\_ddns\_rule**. Save the ARN, as you need it to associate the rule with the Lambda function and to set the appropriate Lambda permissions.

Next, set the target of the rule to be the Lambda function.  Note that the **--targets** input parameter requires that you include a unique identifier for the **Id** target.  You also need to update the command to use the ARN of the Lambda function that you created previously.
```
aws events put-targets --rule ec2_lambda_ddns_rule --targets Id=id123456789012,Arn=<enter-your-lambda-function-arn-here>
```
Next, you add the permissions required for the CloudWatch Events rule to execute the Lambda function.   Note that you need to provide a unique value for the **--statement-id** input parameter.  You also need to provide the ARN of the CloudWatch Events rule you created earlier.
```
aws lambda add-permission --function-name ddns_lambda --statement-id 45 --action lambda:InvokeFunction --principal events.amazonaws.com --source-arn <enter-your-cloudwatch-events-rule-arn-here>
```
#####Step 4 – Create the private hosted zone in Route 53

To create the private hosted zone in Route 53, follow the steps outlined in [Creating a Private Hosted Zone](http://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zone-private-creating.html).

#####Step 5 – Create a DHCP options set and associate it with the VPC

In this step, you create a new DHCP options set and set the domain to be that of your private hosted zone.

1) Follow the steps outlined in [Creating a DHCP Options Set](http://docs.aws.amazon.com/AmazonVPC/latest/UserGuide/VPC_DHCP_Options.html#CreatingaDHCPOptionSet) to create a new set of DHCP options.

2) In the **Create DHCP options set** dialog box, give the new options set a name, set **Domain name** to the name of the private hosted zone that you created in Route 53, and set **Domain name servers** to “AmazonProvidedDNS”.  Choose **Yes, Create**.

