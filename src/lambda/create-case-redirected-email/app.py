import boto3
import json
import urllib.request
from email import policy
from email.parser import BytesParser
from datetime import datetime, timedelta
import os
import time

connect = boto3.client("connect")
cases = boto3.client("connectcases")
profiles = boto3.client("customer-profiles")
# Config propios
DOMAIN_NAME = os.environ["CUSTOMER_PROFILE_DOMAIN"]
INSTANCE_ID = os.environ.get("INSTANCE_ID")
DOMAIN_ID = os.environ.get("CASES_DOMAIN_ID")
TEMPLATE_ID = os.environ.get("CASES_TEMPLATE_ID")
SUBJECT_FIELD_ID = os.environ.get("SUBJECT_FIELD_ID")
DESCRIPTION_FIELD_ID = os.environ.get("DESCRIPTION_FIELD_ID")
CUSTOMER_PROFILE_DOMAIN = os.environ.get("CUSTOMER_PROFILE_DOMAIN")
CUSTOMER_PROFILE_ARN = os.environ.get("CUSTOMER_PROFILE_ARN")


def lambda_handler(event, context):
    print("Event recibido:", event)

    details = event.get("Details", {})
    contact_data = details.get("ContactData", {})
    contact_id = contact_data.get("ContactId")
    instance_arn = contact_data.get("InstanceARN") or contact_data.get("InstanceId")
    instance_id = instance_arn.split("/")[-1] if instance_arn else INSTANCE_ID

    email = contact_data.get("CustomerEndpoint", {}).get("Address")
    if not email:
        # logger.error("No se encontró la dirección de email en el evento")
        return {
            "statusCode": 400,
            "body": json.dumps("Email address not found in event"),
        }

    search_response = profiles.search_profiles(
        DomainName=DOMAIN_NAME, KeyName="_email", Values=[email]
    )
    if search_response.get("Items"):
        profile_id = search_response["Items"][0]["ProfileId"]
        print("Perfil existente:", profile_id)
    else:
        print("Perfil no encontrado. Creando nuevo...")
        create_response = profiles.create_profile(
            DomainName=DOMAIN_NAME,
            EmailAddress=email,
            Attributes={"source": "Email redirect"},
        )
        profile_id = create_response["ProfileId"]
        print("Perfil creado:", profile_id)
    profile_arn = CUSTOMER_PROFILE_ARN + profile_id
    print("ARN del perfil:", profile_arn)
    fields_payload = [
        {
            "id": SUBJECT_FIELD_ID,
            "value": {"stringValue": contact_data.get("InitialContactId", "")},
        },
        {
            "id": DESCRIPTION_FIELD_ID,
            "value": {"stringValue": "test"},
        },
        {"id": "customer_id", "value": {"stringValue": profile_arn}},
        {"id": "title", "value": {"stringValue": "EMAIL PRUEBA"}},
    ]
    print(f"Creando case en ConnectCases con payload: {fields_payload}")
    case_resp = cases.create_case(
        domainId=DOMAIN_ID, templateId=TEMPLATE_ID, fields=fields_payload
    )
    print("Case creado:", case_resp)
    # logger.info(f"Case creado con ID: {case_resp.get('caseId')}")
    return {"status": "ok", "caseId": case_resp.get("caseId")}