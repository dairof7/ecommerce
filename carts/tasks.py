# carts/tasks.py
from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML, CSS
from .models import Quote

def get_shop_info():
    """Helper para obtener la información de la tienda desde settings."""
    return {
        'nombre_empresa': settings.SHOP_COMPANY_NAME,
        'nit': settings.SHOP_COMPANY_NIT,
        'nombre': settings.SHOP_SELLER_NAME,
        'cedula': settings.SHOP_SELLER_ID,
        'direccion': settings.SHOP_ADDRESS,
        'telefono': settings.SHOP_PHONE,
        'correo': settings.SHOP_EMAIL,
        'logo_url': settings.SHOP_LOGO_URL
    }

def generate_receipt_pdf(quote, shop_info, customer_info):
    """
    Genera el PDF del recibo de venta / ticket (58mm con altura dinámica),
    exactamente igual al que se visualiza desde la gestión de pedidos en el admin.
    """
    base_height_mm = 90
    if quote.paid_amount and quote.paid_amount > 0:
        base_height_mm += 14
    if quote.notes:
        base_height_mm += 20
    num_items = quote.items.count()
    total_height = max(60, base_height_mm + (num_items * 12))

    context = {
        'document': quote,
        'shop_info': shop_info,
        'customer_info': customer_info,
    }
    html_string = render_to_string('carts/pdf/receipt_58mm_template.html', context)
    css = CSS(string=f'@page {{ size: 58mm {total_height}mm; margin: 0mm; }}')
    return HTML(string=html_string).write_pdf(stylesheets=[css])

@shared_task
def send_quote_pdf_email(quote_id):
    try:
        # Hacemos prefetch de todo lo que podríamos necesitar, incluso si user es None
        quote = Quote.objects.select_related('user', 'user__profile').prefetch_related('items', 'items__product').get(id=quote_id)
        
        shop_info = get_shop_info()
        subject = f'Cotización #{quote.id} de {shop_info["nombre_empresa"]}'
        
        # --- Lógica para determinar los datos del cliente ---
        if quote.user:
            # La cotización es de un usuario registrado (priorizando datos corregidos en quote si existen)
            customer_name = quote.customer_name or quote.user.get_full_name() or quote.user.username
            customer_email = quote.customer_email or quote.user.email
            customer_document = quote.customer_document or getattr(quote.user.profile, 'document', 'No especificado')
            customer_phone = quote.customer_phone or getattr(quote.user.profile, 'phone', 'No especificado')
            customer_address = quote.customer_address or getattr(quote.user.profile, 'address', 'No especificada')
        else:
            # La cotización es de un cliente invitado
            customer_name = quote.customer_name or 'N/A'
            customer_email = quote.customer_email
            customer_document = quote.customer_document or 'No especificado'
            customer_phone = quote.customer_phone or 'No especificado'
            customer_address = quote.customer_address or 'No especificada'
        
        # Asegurarse de que tenemos un email a donde enviar
        if not customer_email:
            return f"Error: Cotización #{quote_id} no tiene un email de destino (ni usuario registrado, ni email de invitado)."

        # Construir el cuerpo del mensaje
        if quote.paid_amount and quote.paid_amount > 0:
            message_text = (
                f'Hola {customer_name},\n\n'
                f'Gracias por tu interés en {shop_info["nombre_empresa"]}. Adjuntamos la cotización y recibo de tu pedido #{quote.id}.\n\n'
                f'• Total cotización: ${int(quote.total):,}\n'
                f'• Abono inicial: ${int(quote.paid_amount):,}\n'
                f'• Saldo pendiente: ${int(quote.pending_balance):,}\n'
                + (f'• Observaciones: {quote.notes}\n' if quote.notes else '')
                + f'\nPara continuar con tu compra, contáctanos por WhatsApp al {shop_info["telefono"]}.'
            )
        else:
            message_text = f'Hola {customer_name},\n\nGracias por tu interés en {shop_info["nombre_empresa"]}. Adjuntamos el PDF con los detalles de tu cotización.\n\nPara continuar, contáctanos por WhatsApp al {shop_info["telefono"]}.'
        
        from_email = settings.EMAIL_HOST_USER
        to_email = [customer_email]

        # Pasar un diccionario de cliente unificado a la plantilla
        customer_info = {
            'name': customer_name,
            'email': customer_email,
            'document': customer_document,
            'phone': customer_phone,
            'address': customer_address, # Este campo es útil para la factura
        }

        context = {
            'document': quote,
            'shop_info': shop_info,
            'customer_info': customer_info # Pasamos los datos del cliente unificados
        }
        
        html_string = render_to_string('carts/pdf/quote_template.html', context)
        pdf_file = HTML(string=html_string).write_pdf()
        receipt_pdf = generate_receipt_pdf(quote, shop_info, customer_info)

        email = EmailMessage(subject, message_text, from_email, to_email)
        email.attach(f'cotizacion_{quote.id}.pdf', pdf_file, 'application/pdf')
        email.attach(f'recibo_{quote.id}.pdf', receipt_pdf, 'application/pdf')
        email.send()
        
        return f"Correo de cotización #{quote_id} enviado a {customer_email}"
    except Quote.DoesNotExist:
        return f"Error: Cotización con ID {quote_id} no encontrada."
    except Exception as e:
        return f"Error al enviar correo de cotización #{quote_id}: {str(e)}"

# Deberías aplicar una lógica similar a send_invoice_pdf_email
@shared_task
def send_invoice_pdf_email(quote_id):
    try:
        invoice = Quote.objects.select_related('user', 'user__profile').prefetch_related('items', 'items__product').get(id=quote_id)
        
        shop_info = get_shop_info()
        subject = f'Factura de Venta #{invoice.id} de {shop_info["nombre_empresa"]}'
        
        if invoice.user:
            customer_name = invoice.customer_name or invoice.user.get_full_name() or invoice.user.username
            customer_email = invoice.customer_email or invoice.user.email
            customer_document = invoice.customer_document or getattr(invoice.user.profile, 'document', 'No especificado')
            customer_phone = invoice.customer_phone or getattr(invoice.user.profile, 'phone', 'No especificado')
            customer_address = invoice.customer_address or getattr(invoice.user.profile, 'address', 'No especificada')
        else:
            customer_name = invoice.customer_name or 'N/A'
            customer_email = invoice.customer_email
            customer_document = invoice.customer_document or 'No especificado'
            customer_phone = invoice.customer_phone or 'No especificado'
            customer_address = invoice.customer_address or 'No especificada'
        
        if not customer_email:
            return f"Error: Factura #{quote_id} no tiene un email de destino."
            
        if invoice.paid_amount and invoice.paid_amount > 0:
            message_text = (
                f'Hola {customer_name},\n\n'
                f'Gracias por tu compra en {shop_info["nombre_empresa"]}. Adjuntamos la factura y el recibo de venta para tu pedido #{invoice.id}.\n\n'
                f'• Total pedido: ${int(invoice.total):,}\n'
                f'• Abono inicial recibido: ${int(invoice.paid_amount):,}\n'
                f'• Saldo pendiente: ${int(invoice.pending_balance):,}\n'
                + (f'• Observaciones: {invoice.notes}\n' if invoice.notes else '')
                + f'\n¡Esperamos verte de nuevo pronto!'
            )
        else:
            message_text = f'Hola {customer_name},\n\nGracias por tu compra en {shop_info["nombre_empresa"]}. Adjuntamos la factura y el recibo de venta para tu pedido #{invoice.id}.\n\n¡Esperamos verte de nuevo pronto!'
        from_email = settings.EMAIL_HOST_USER
        to_email = [customer_email]

        customer_info = {
            'name': customer_name,
            'email': customer_email,
            'document': customer_document,
            'phone': customer_phone,
            'address': customer_address
        }

        context = {
            'document': invoice,
            'shop_info': shop_info,
            'customer_info': customer_info,
            'vendedor_info': { # Alinear nombre con get_shop_info
                'nombre_empresa': shop_info['nombre_empresa'],
                'nit': shop_info['nit'],
                'nombre': shop_info['nombre'],
                'cedula': shop_info['cedula'],
            }
        }
        
        html_string = render_to_string('carts/pdf/invoice_template.html', context)
        pdf_file = HTML(string=html_string).write_pdf()
        receipt_pdf = generate_receipt_pdf(invoice, shop_info, customer_info)

        email = EmailMessage(subject, message_text, from_email, to_email)
        email.attach(f'factura_{invoice.id}.pdf', pdf_file, 'application/pdf')
        email.attach(f'recibo_{invoice.id}.pdf', receipt_pdf, 'application/pdf')
        email.send()
        
        return f"Correo de factura #{invoice.id} enviado a {customer_email}."
    except Exception as e:
        return f"Error al enviar correo de factura #{quote_id}: {str(e)}"


@shared_task
def send_backorder_email(quote_id):
    """
    Envía un correo al cliente confirmando que su pedido bajo pedido
    fue registrado y está pendiente de llegada de stock.
    """
    try:
        quote = Quote.objects.select_related('user', 'user__profile').prefetch_related('items', 'items__product').get(id=quote_id)

        shop_info = get_shop_info()
        subject = f'Pedido #{quote.id} confirmado - {shop_info["nombre_empresa"]} (En camino)'

        if quote.user:
            customer_name = quote.customer_name or quote.user.get_full_name() or quote.user.username
            customer_email = quote.customer_email or quote.user.email
            customer_document = quote.customer_document or getattr(quote.user.profile, 'document', 'No especificado')
            customer_phone = quote.customer_phone or getattr(quote.user.profile, 'phone', 'No especificado')
            customer_address = quote.customer_address or getattr(quote.user.profile, 'address', 'No especificada')
        else:
            customer_name = quote.customer_name or 'N/A'
            customer_email = quote.customer_email
            customer_document = quote.customer_document or 'No especificado'
            customer_phone = quote.customer_phone or 'No especificado'
            customer_address = quote.customer_address or 'No especificada'

        if not customer_email:
            return f"Error: Pedido #{quote_id} no tiene email de destino."

        message_text = (
            f'Hola {customer_name},\n\n'
            f'Tu pedido #{quote.id} ha sido confirmado y registrado.\n'
            f'Los productos están siendo conseguidos y te notificaremos cuando estén listos para despacho.\n\n'
            f'Para cualquier consulta, contáctanos por WhatsApp.\n\n'
            f'¡Gracias por tu compra!'
        )
        from_email = settings.EMAIL_HOST_USER
        to_email = [customer_email]

        customer_info = {
            'name': customer_name,
            'email': customer_email,
            'document': customer_document,
            'phone': customer_phone,
            'address': customer_address,
        }

        context = {
            'document': quote,
            'shop_info': shop_info,
            'customer_info': customer_info,
            'vendedor_info': {
                'nombre_empresa': shop_info['nombre_empresa'],
                'nit': shop_info['nit'],
                'nombre': shop_info['nombre'],
                'cedula': shop_info['cedula'],
            }
        }

        html_string = render_to_string('carts/pdf/invoice_template.html', context)
        pdf_file = HTML(string=html_string).write_pdf()
        receipt_pdf = generate_receipt_pdf(quote, shop_info, customer_info)

        email = EmailMessage(subject, message_text, from_email, to_email)
        email.attach(f'pedido_{quote.id}.pdf', pdf_file, 'application/pdf')
        email.attach(f'recibo_{quote.id}.pdf', receipt_pdf, 'application/pdf')
        email.send()

        return f"Correo de backorder #{quote_id} enviado a {customer_email}."
    except Quote.DoesNotExist:
        return f"Error: Pedido con ID {quote_id} no encontrado."
    except Exception as e:
        return f"Error al enviar correo de backorder #{quote_id}: {str(e)}"