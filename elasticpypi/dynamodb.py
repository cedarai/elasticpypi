import urllib
import re
import boto3
from boto3.dynamodb.conditions import Key
from elasticpypi import name
from elasticpypi.config import config

TABLE = config['table']


def list_packages(dynamodb):
    table = dynamodb.Table(TABLE)
    dynamodb_packages = table.scan(ProjectionExpression='normalized_name')
    package_set = set()
    for package in dynamodb_packages['Items']:
        package_set.add(package['normalized_name'])
    packages = [(package, package) for package in sorted(package_set)]
    return packages


def list_packages_by_name(dynamodb, package_name):
    _name = name.normalize(package_name)
    table = dynamodb.Table(TABLE)
    dynamodb_packages = table.query(
        IndexName='normalized_name-index',
        KeyConditionExpression=Key('normalized_name').eq(_name),
        ProjectionExpression='filename',
        ScanIndexForward=False,
    )
    sorted_packages = sorted(dynamodb_packages['Items'], key=lambda k: k['filename'])
    packages = [(package['filename'], package['filename']) for package in sorted_packages]
    return packages


def get_max_version_by_name(dynamodb, package_name, major_version):
    _name = name.normalize(package_name)
    table = dynamodb.Table(TABLE)
    dynamodb_packages = table.query(
        IndexName='name_major_version-index',
        KeyConditionExpression=Key('name_major_version').eq('%s-%s' % (_name, major_version)),
        ProjectionExpression='version',
        ScanIndexForward=False,
        Limit=1,
    )
    if dynamodb_packages['Items']:
        ver = dynamodb_packages['Items'][0]['version']
        return ver
    else:
        return '%s.0' % major_version


def delete_item(version, table, filename):
    table.delete_item(
        Key={
            'package_name': filename,
            'version': version,
        },
    )


def put_item(version, filename, normalized_name, table):
    vp = version.split('.')
    name_major_version = '%s-%s.%s' % (normalized_name, vp[0], vp[1])
    minor_version = int(vp[2])
    table.put_item(
        Item={
            'package_name': urllib.parse.unquote_plus(filename),
            'version': urllib.parse.unquote_plus(version),
            'filename': urllib.parse.unquote_plus(filename),
            'normalized_name': urllib.parse.unquote_plus(normalized_name),
            'name_major_version': urllib.parse.unquote_plus(name_major_version),
            'minor_version': minor_version,
        }
    )


def exists(filename):
    db = boto3.resource('dynamodb')
    table = db.Table(TABLE)
    dynamodb_packages = table.query(
        KeyConditionExpression=Key('package_name').eq(filename),
        ProjectionExpression='filename',
        ScanIndexForward=False,
    )
    return dynamodb_packages.get('Count', 0)
