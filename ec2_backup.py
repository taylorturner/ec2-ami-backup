import boto3
import collections
import datetime
import time
import sys

today = datetime.date.today()
today_string = today.strftime('%Y/%m/%d')
delete_after_days = 7  # delete snapshot after 7 days

ec2 = boto3.client('ec2')
regions = ec2.describe_regions().get('Regions', [])
all_regions = [region['RegionName'] for region in regions]

deletion_date = today - datetime.timedelta(days=delete_after_days)
deletion_date_string = deletion_date.strftime('%Y/%m/%d')

# def lambda_handler(event, context):
snapshot_counter = 0
deletion_counter = 0

for region_name in all_regions:
    print(f'Instances in EC2 Region {region_name}:')
    ec2 = boto3.resource('ec2', region_name=region_name)

    instances = ec2.instances.filter(
        Filters=[
            {'Name': 'tag:Backup', 'Values': ['true']}
        ])

    for i in instances.all():

        for tag in i.tags:  # get instance name
            if tag['Key'] == 'Name':
                name = tag['Value']

        print(f"Found tagged instance \'{name}\' id: {i.id}, state: {i.state['Name']}")

        try:
            snapshot = i.create_image(
                Name="{0}-{1}-auto_backup".format(name, today_string),
                Description="Automated AMI backup of {0} - created {1}".format(name, today_string),
                NoReboot=True
            )

            snapshot.create_tags(
                Tags=[
                    {'Key': 'auto_backup', 'Value': 'true'},
                    {'Key': 'CreatedOn', 'Value': today_string}
                ])
            print('AMI image created')
            snapshot_counter += 1
        except:
            print(f"Instance: {name} already has a backup from today")

        images = ec2.images.filter(
            Filters=[
                {'Name': 'tag:auto_backup', 'Values': ['true']}
            ])

        print(f'Checking for backups that are older than {delete_after_days} days for instance {name}')
        for i in images:
            can_delete = False
            for tag in i.tags:
                if tag['Key'] == 'CreatedOn':
                    created_on_string = tag['Value']
                if tag['Key'] == 'auto_backup':
                    if tag['Value'] == 'true':
                        can_delete = True
                if tag['Key'] == 'Name':
                    name = tag['Value']
            created_on = datetime.datetime.strptime(created_on_string, '%Y/%m/%d').date()

            if created_on <= deletion_date and can_delete == True:
                print(f'Image id {i.id}, ({name}) from {created_on_string} is {delete_after_days} or more days old... deleting')
                i.deregister()
                deletion_counter += 1

print(f'    Made {snapshot_counter} backups, deleted {deletion_counter} backups')
# return
