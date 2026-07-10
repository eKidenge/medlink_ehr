import csv
from django.http import HttpResponse
from openpyxl import Workbook

def export_to_csv(queryset, fields):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="export.csv"'

    writer = csv.writer(response)
    writer.writerow(fields)

    for obj in queryset:
        writer.writerow([getattr(obj, field) for field in fields])

    return response


def export_to_excel(queryset, fields):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(fields)

    for obj in queryset:
        sheet.append([getattr(obj, field) for field in fields])

    response = HttpResponse(
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename="export.xlsx"'

    workbook.save(response)
    return response