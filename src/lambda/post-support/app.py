import boto3
import os
import json
import uuid
from datetime import datetime

profiles = boto3.client('customer-profiles')
cases = boto3.client('connectcases')
s3 = boto3.client('s3')  # <--- cliente S3
ses = boto3.client("ses")

def lambda_handler(event, context):
    print("EVENT:", json.dumps(event))

    try:
        domain_name = os.environ["CUSTOMER_PROFILE_DOMAIN"]
        cases_domain_id = os.environ["CASES_DOMAIN_ID"]
        cases_template_id = os.environ["CASES_TEMPLATE_ID"]
        s3_bucket_name = os.environ["S3_CASES_BUCKET"]
        sender_email = os.environ["SES_SENDER_EMAIL"]

        name = event.get("name", "").strip()
        email = event.get("email", "").strip()
        phone = event.get("phoneNumber", "").strip()
        subject = event.get("subject", "Sin título")
        description = event.get("description", "")
        nivel = event.get("nivel", "LEVE")

        if not email:
            return {
                "statusCode": 400,
                "body": "Error: Email es obligatorio"
            }

        print("Buscando perfil por email...")
        search_response = profiles.search_profiles(
            DomainName=domain_name,
            KeyName="EmailAddress",
            Values=[email]
        )

        if search_response.get("Items"):
            profile_id = search_response["Items"][0]["ProfileId"]
            print("Perfil existente:", profile_id)
        else:
            print("Perfil no encontrado. Creando nuevo...")
            create_response = profiles.create_profile(
                DomainName=domain_name,
                EmailAddress=email,
                FirstName=name,
                # PhoneNumber=phone,
                Attributes={
                    "description": description,
                    "nivel": nivel
                }
            )
            profile_id = create_response["ProfileId"]
            print("Perfil creado:", profile_id)

        region = boto3.session.Session().region_name
        account_id = boto3.client("sts").get_caller_identity()["Account"]
        customer_id = f"arn:aws:profiles:{region}:{account_id}:domains/{domain_name}/profiles/{profile_id}"
        print("ARN construido:", customer_id)

        fields = [
            {
                "id": "customer_id",
                "value": {
                    "stringValue": customer_id
                }
            },
            {
                "id": "title",
                "value": {
                    "stringValue": subject
                }
            }
        ]

        print("Enviando creación del caso...")
        case_response = cases.create_case(
            domainId=cases_domain_id,
            templateId=cases_template_id,
            fields=fields
        )

        case_id = case_response.get("caseId")
        print("Caso creado:", case_id)

        # Guardar en S3
        timestamp = datetime.utcnow().isoformat()
        file_key = f"cases/{case_id}_{uuid.uuid4().hex}.json"
        case_data = {
            "caseId": case_id,
            "profileId": profile_id,
            "customerId": customer_id,
            "subject": subject,
            "description": description,
            "nivel": nivel,
            "email": email,
            # "phone": phone,
            "timestamp": timestamp
        }

        s3.put_object(
            Bucket=s3_bucket_name,
            Key=file_key,
            Body=json.dumps(case_data),
            ContentType="application/json"
        )
        print("Caso guardado en S3:", file_key)

        # Enviar notificación por SES
        email_subject = f"Confirmación de creación de caso #{case_id}"
        email_body = f"""
        Hola {name or 'usuario'},

        Tu caso ha sido creado correctamente en nuestro sistema.
        
        Número de caso: {case_id}
        Asunto: {subject}
        Descripción: {description}
        Nivel: {nivel}
        
        Te contactaremos a la brevedad.
        
        Saludos,
        Soporte Técnico
        """
        
        ses.send_email(
            Source=sender_email,
            Destination={
                "ToAddresses": [email]
            },
            Message={
                "Subject": {
                    "Data": email_subject,
                    "Charset": "UTF-8"
                },
                "Body": {
                    "Text": {
                        "Data": email_body,
                        "Charset": "UTF-8"
                    }
                }
            }
        )
        print(f"Email de confirmación enviado a {email}")

        return {
            "statusCode": 201,
            "body": {
                "message": "notificado por correo exitosamente",
                "caseId": case_id,
                "s3Key": file_key
            }
        }
    
    except Exception as e:
        print("ERROR:", str(e))
        return {
            "statusCode": 500,
            "body": f"Error: {str(e)}"
        }