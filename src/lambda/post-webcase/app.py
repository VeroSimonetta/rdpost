import boto3
import os
import json
import uuid
from datetime import datetime

profiles = boto3.client('customer-profiles')
cases = boto3.client('connectcases')
s3 = boto3.client('s3') 
ses = boto3.client("ses")
sns = boto3.client("sns")
account_id = boto3.client("sts").get_caller_identity()["Account"]
region = boto3.session.Session().region_name
domain_name = os.environ["CUSTOMER_PROFILE_DOMAIN"]
cases_domain_id = os.environ["CASES_DOMAIN_ID"]
cases_template_id = os.environ["CASES_TEMPLATE_ID"]
s3_bucket_name = os.environ["S3_CASES_BUCKET"]

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))

    attributes = event.get("Details", {}).get("ContactData", {}).get("Attributes", {})

    subject = attributes.get("subject", "Sin título")
    description = attributes.get("description", "")
    nombre_val = attributes.get("nombre", "")

        # profile_id = event.get("profileId")
        # email_val = ""
        # if profile_id:
        #     profile = profiles.get_profile(
        #         DomainName=os.environ["CUSTOMER_PROFILE_DOMAIN"],
        #         ProfileId=profile_id
        #     )
        #     email_val = profile.get("Profile", {}).get("EmailAddress")
        #     if not email_val:
        #       email_val = event.get("email")
        
        # print("Email recuperado:", email_val)
        # if not email:
        #     return {
        #         "statusCode": 400,
        #         "body": "Error: Email es obligatorio"
        #     }

        #print("Buscando perfil por email...")
        # search_response = profiles.search_profiles(
        #     DomainName=domain_name,
        #     KeyName="EmailAddress",
        #     Values=[email]
        # )

        # if search_response.get("Items"):
        #     profile_id = search_response["Items"][0]["ProfileId"]
        #     print("Perfil existente:", profile_id)
        # else:
        #     print("Perfil no encontrado. Creando nuevo...")
        #     create_response = profiles.create_profile(
        #         DomainName=domain_name,
        #         EmailAddress=email,
        #         FirstName=name,
        #         # PhoneNumber=phone,
        #         Attributes={
        #             "description": description,
        #             "nivel": nivel
        #         }
        #     )
        #     profile_id = create_response["ProfileId"]
        #     print("Perfil creado:", profile_id)


    allFields = cases.list_fields(domainId=cases_domain_id)
    fields = {}
    for field in allFields["fields"]:
        fields[field["name"]] = field["fieldId"]
    completeFields = []
    for key, value in fields.items():
        if key in attributes:
            completeFields.append(
                {
                    "id": fields[key],
                    "value": {"stringValue": attributes[key]},
                }
            )
    customerARN = f"arn:aws:profiles:{region}:{account_id}:domains/{domain_name}/profiles/0e845b377127401aa7b6f406b102b537"
    print("ARN construido:", customerARN)       
    completeFields.append(
        {
            "id": "customer_id",
            "value": {"stringValue": customerARN},
        }
    )
    completeFields.append(
        {
            "id": "title",
            "value": {"stringValue": 'caso nuevo'},
        }
    )

    print("Enviando creación del caso...")
    case_response = cases.create_case(
        domainId=cases_domain_id,
        templateId=cases_template_id,
        fields=completeFields
    )

    case_id = case_response.get("caseId")
    print("Caso creado:", case_id)

    # # Guardar en S3
    # timestamp = datetime.utcnow().isoformat()
    # file_key = f"cases/{case_id}_{uuid.uuid4().hex}.json"
    # case_data = {
    #     "caseId": case_id,
    #     #"profileId": profile_id,
    #     "customerId": customer_id,
    #     "subject": subject,
    #     "description": description,
    #     "nivel": nivel,
    #     "email": email,
    #     "nombre": nombre_val,
    #     "apellidos": apellidos_val,
    #     "telefono": telefono_val,
    #     "email": email_val, 
    #     "tipoConsulta": tipoConsulta_val,
    #     "subtipoInfo": subtipoInfo_val,
    #     "subtipoSolicitud": subtipoSolicitud_val,
    #     "numeroEnvio": numeroEnvio_val,
    #     "direccion": direccion_val,
    #     "codigoPostal": codigoPostal_val,
    #     "motivoConsulta": motivoConsulta_val,
    #     "timestamp": timestamp
    # }

    # s3.put_object(
    #     Bucket=s3_bucket_name,
    #     Key=file_key,
    #     Body=json.dumps(case_data),
    #     ContentType="application/json"
    # )
    # print("Caso guardado en S3:", file_key)

    # Enviar notificación por SES
    email_subject = f"Confirmación de creación de caso #{case_id}"
    email_body = f"""
    Hola {nombre_val or 'usuario'},

    Tu caso ha sido creado correctamente en nuestro sistema.
    
    Número de caso: {case_id}
    Asunto: {subject}
    Descripción: {description}
    
    Te contactaremos a la brevedad.
    
    Saludos,
    Soporte Técnico
    """
    sns.publish(
        TopicArn='arn:aws:sns:eu-central-1:805246628735:test_notification',
        Message=email_body,
        Subject='Test envio desde sns',
    )

    return {
        "statusCode": 201,
        "body": {
            "message": "notificado por correo exitosamente",
            "caseId": case_id
        }
    }
    