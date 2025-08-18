import os
import boto3
import json

cases = boto3.client("connectcases")
profiles = boto3.client("customer-profiles")

# Variables de entorno
DOMAIN_NAME = os.environ["CUSTOMER_PROFILE_DOMAIN"]
DOMAIN_ID = os.environ["CASES_DOMAIN_ID"]
TEMPLATE_ID = os.environ["CASES_TEMPLATE_ID"]
SUBJECT_FIELD_ID = os.environ["SUBJECT_FIELD_ID"]
DESCRIPTION_FIELD_ID = os.environ["DESCRIPTION_FIELD_ID"]
CUSTOMER_PROFILE_ARN = os.environ.get("CUSTOMER_PROFILE_ARN")  # base ARN para construir profileArn
PHONE_FIELD_ID = os.environ.get("PHONE_FIELD_ID")  # opcional

def lambda_handler(event, context):
    print("EVENT recibido:", json.dumps(event))

    details = event.get("Details", {})
    contact_data = details.get("ContactData", {})
    contact_id = contact_data.get("ContactId")
    initial_contact_id = contact_data.get("InitialContactId", contact_id)

    # Información del cliente
    customer_endpoint = contact_data.get("CustomerEndpoint", {})
    contact_type = customer_endpoint.get("Type")
    contact_address = customer_endpoint.get("Address")
    customer_name = contact_data.get("Attributes", {}).get("Name", "Cliente desconocido")

    if not contact_address:
        return {"status": "ERROR", "message": "No se encontró la dirección de contacto"}

    # Buscar o crear perfil en Customer Profiles
    if contact_type == "TELEPHONE_NUMBER":
        search_key = "_phone"
        search_value = contact_address
    else:
        return {"status": "ERROR", "message": f"Tipo de contacto no soportado: {contact_type}"}

    # Buscar perfil existente
    search_response = profiles.search_profiles(
        DomainName=DOMAIN_NAME, KeyName=search_key, Values=[search_value]
    )

    if search_response.get("Items"):
        profile_id = search_response["Items"][0]["ProfileId"]
        print("Perfil existente:", profile_id)
    else:
        # Crear perfil nuevo
        create_response = profiles.create_profile(
            DomainName=DOMAIN_NAME,
            PhoneNumber=contact_address,
            Attributes={"source": "Phone call"},
        )
        profile_id = create_response["ProfileId"]
        print("Perfil creado:", profile_id)

    profile_arn = CUSTOMER_PROFILE_ARN + profile_id
    print("ARN del perfil:", profile_arn)

    # Payload de campos para Connect Cases
    fields_payload = [
        {"id": SUBJECT_FIELD_ID, "value": {"stringValue": contact_data.get("InitialContactId", "")}},
        {"id": DESCRIPTION_FIELD_ID, "value": {"stringValue": f"Case generado automáticamente para {customer_name}."}},
        {"id": "customer_id", "value": {"stringValue": profile_arn}},
         {"id": "title", "value": {"stringValue": "Llamada de prueba test Lucho"}},
    ]

    if PHONE_FIELD_ID:
        fields_payload.append({"id": PHONE_FIELD_ID, "value": {"stringValue": contact_address}})

    print(f"Creando case en ConnectCases con payload: {fields_payload}")

    # Crear el case
    case_resp = cases.create_case(
        domainId=DOMAIN_ID, templateId=TEMPLATE_ID, fields=fields_payload
    )

    print("Case creado:", case_resp)
    return {"status": "OK", "caseId": case_resp.get("caseId"), "caseArn": case_resp.get("caseArn")}