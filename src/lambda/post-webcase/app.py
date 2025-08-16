import json
#import boto3
import os

#dynamodb = boto3.resource('dynamodb')

"""
    Función principal de Lambda que procesa las solicitudes de API Gateway
    para cargar datos 
"""
def lambda_handler(event, context):

   # table_name = os.environ['DYNAMODB_TABLE_NAME']
   # table = dynamodb.Table(table_name)

    # Extrae el cuerpo de la solicitud (body) de la API Gateway
    try:
        body = json.loads(event['body'])
    except KeyError:
        return {
            'statusCode': 400,
            'body': json.dumps('Error: No se encontró el cuerpo de la solicitud (body).')
        }
    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps('Error: El formato del cuerpo de la solicitud no es JSON válido.')
        }

    # Valida que los datos necesarios estén presentes en el cuerpo
    if 'nombre' not in body or 'apellido' not in body:
        return {
            'statusCode': 400,
            'body': json.dumps('Error: Los campos "nombre" y "apellido" son obligatorios.')
        }

    # Carga los datos en la tabla de DynamoDB
    try:
       # table.put_item(
        #    Item={
        #        'pk': body['id'],
        #        'data': body['data']
        #    }
        #)
        print(body['nombre'])
        return {
            'statusCode': 201,
            'body': json.dumps('¡Datos cargados con éxito!')
        }
    except Exception as e:
        print(e)
        return {
            'statusCode': 500,
            'body': json.dumps('Error interno del servidor al cargar los datos.')
        }