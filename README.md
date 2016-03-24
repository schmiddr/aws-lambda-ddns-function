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
