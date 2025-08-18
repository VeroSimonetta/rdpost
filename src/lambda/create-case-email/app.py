import json
import boto3
import email
from email import policy
import os

s3 = boto3.client('s3')
profiles = boto3.client('customer-profiles')
cases = boto3.client('connectcases')
ses = boto3.client('ses') 

DOMAIN_NAME = os.environ['CUSTOMER_PROFILE_DOMAIN']
CASES_DOMAIN_ID = os.environ['CASES_DOMAIN_ID']
TEMPLATE_ID = os.environ['CASES_TEMPLATE_ID']

# Reemplazá estos con los IDs REALES de tu template
# FIELD_ID_SUBJECT = "subject"
# FIELD_ID_DESCRIPTION = "description"
# FIELD_ID_CUSTOMER_ID = "customer_id"
# FIELD_ID_TITLE = "title"
FIELD_ID_SUBJECT = os.environ['FIELD_ID_SUBJECT']
FIELD_ID_DESCRIPTION = os.environ['FIELD_ID_DESCRIPTION']
FIELD_ID_CUSTOMER_ID = "customer_id"
FIELD_ID_TITLE = os.environ['FIELD_ID_TITLE']
FROM_EMAIL = os.environ.get('SES_FROM_EMAIL') 


def lambda_handler(event, context):
    try:
        # funcion para obtener los ids del template cases
        # response = cases.list_fields(
        #     domainId=CASES_DOMAIN_ID,
        # )

        # fields = response.get('fields', [])

        # for field in fields:
        #     print(f"Name: {field['name']} | FieldId: {field['fieldId']} | Type: {field['type']}")
        #     if field['name'] == 'Title':
        #         print(f"\ FieldId del campo 'Title': {field['fieldId']}")

        # return {
        #     "statusCode": 200,
        #     "body": "Campos listados correctamente"
        # }

        record = event['Records'][0]
        bucket_name = record['s3']['bucket']['name']
        object_key = record['s3']['object']['key']
        
        print("Email recibido:", object_key)

        # Obtener el email desde S3
        raw_email = s3.get_object(Bucket=bucket_name, Key=object_key)['Body'].read()

        # Parsear el email
        msg = email.message_from_bytes(raw_email, policy=policy.default)
        from_email = email.utils.parseaddr(msg['From'])[1]

        if not from_email:
            raise Exception("ERROR: No se pudo extraer una dirección de correo válida del campo 'From'.")

        subject = msg['Subject'] or "Sin asunto"
        body = msg.get_body(preferencelist=('plain')).get_content() if msg.is_multipart() else msg.get_payload()

        print(f"Remitente: {from_email}")
        print(f"Asunto: {subject}")

        # Buscar perfil por email
        search_response = profiles.search_profiles(
            DomainName=DOMAIN_NAME,
            KeyName="EmailAddress",
            Values=[from_email]
        )

        if search_response.get("Items"):
            profile_id = search_response["Items"][0]["ProfileId"]
            print("Perfil existente:", profile_id)
        else:
            print("Perfil no encontrado. Creando nuevo...")
            create_response = profiles.create_profile(
                DomainName=DOMAIN_NAME,
                EmailAddress=from_email,
                Attributes={
                    "source": "Email redirect",
                    "originalKey": object_key
                }
            )
            profile_id = create_response["ProfileId"]
            print("Perfil creado:", profile_id)

        # Construir ARN del perfil
        region = os.environ.get("AWS_REGION", "eu-central-1")
        account_id = boto3.client('sts').get_caller_identity()['Account']
        profile_arn = f"arn:aws:profiles:{region}:{account_id}:domains/{DOMAIN_NAME}/profiles/{profile_id}"

        # Crear el caso
        response = cases.create_case(
            domainId=CASES_DOMAIN_ID,
            templateId=TEMPLATE_ID,
            fields=[
                {
                    "id": FIELD_ID_TITLE,
                    "value": {"stringValue": body}
                },
                {
                    "id": FIELD_ID_SUBJECT,
                    "value": {"stringValue": subject}
                },
                {
                    "id": FIELD_ID_DESCRIPTION,
                    "value": {"stringValue": body}
                },
                {
                    "id": FIELD_ID_CUSTOMER_ID,
                    "value": {"stringValue": profile_arn}
                }
                # {
                #     "id": "title",
                #     "value": {"stringValue": body}
                # },
                # {
                #     "id": "233b08df-a422-4224-80d0-d4f1108e07d9",  # subject
                #     "value": {"stringValue": subject}
                # },
                # {
                #     "id": "bcb3877c-f297-44d5-9efb-7f5907a5ebdc",  # description
                #     "value": {"stringValue": body}
                # }
            ]
        )

        case_id = response["caseId"]
        print("Caso creado con ID:", case_id)

        # return {
        #     "statusCode": 200,
        #     "body": json.dumps({"message": "Caso creado exitosamente", "caseId": case_id})
        # }

        print("INICIO LAMBDA")
        print("EVENTO:", json.dumps(event))
        # Enviar email de notificación
        ses_response = ses.send_email(
            Source=FROM_EMAIL,
            Destination={"ToAddresses": [FROM_EMAIL]},
            Message={
                "Subject": {
                    "Data": f"Tu caso fue creado: {case_id}",
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": f"""
                                    Hola,

                                    Tu solicitud fue recibida correctamente.

                                    ID del caso: {case_id}
                                    Asunto: {subject}

                                    Nos pondremos en contacto contigo pronto.

                                    Gracias,
                                    Soporte
                                    """,
                        "Charset": "UTF-8"
                    }
                }
            }
        )
        print("RESPUESTA SES:", json.dumps(ses_response))
        print("Email de confirmación enviado:", ses_response['MessageId'])

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Caso creado y correo enviado",
                "caseId": case_id
            })
        }


    except Exception as e:
        print("Error:", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }