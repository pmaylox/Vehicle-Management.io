from battery import battery_summary
from datetime import date
from decimal import Decimal
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter


def style_sheet(sheet, title, headers, rows, widths, formats):
    column_count = len(headers)

    sheet.sheet_view.showGridLines = False
    sheet.merge_cells(
        start_row=1,
        start_column=1,
        end_row=1,
        end_column=column_count
    )

    sheet.cell(1, 1, title)
    sheet.cell(1, 1).font = Font(
        name="Calibri", size=18, bold=True, color="FFFFFF"
    )
    sheet.cell(1, 1).fill = PatternFill(
        "solid", fgColor="17365D"
    )
    sheet.row_dimensions[1].height = 36

    sheet.cell(2, 1, f"Exported {date.today():%m/%d/%Y}")
    sheet.cell(2, 1).font = Font(
        name="Calibri", size=10, color="666666"
    )

    for column, header in enumerate(headers, start=1):
        cell = sheet.cell(4, column, header)
        cell.font = Font(
            name="Calibri", size=12, bold=True, color="FFFFFF"
        )
        cell.fill = PatternFill("solid", fgColor="245A81")
        cell.alignment = Alignment(
            horizontal="center",
            vertical="top", wrap_text=True
        )

    sheet.row_dimensions[4].height = 36

    for row_number, values in enumerate(rows, start=5):
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row_number, column, value)

            # Keep descriptions as text, even if they start with "=".
            if isinstance(value, str):
                cell.data_type = "s"

            cell.font = Font(name="Calibri", size=11)
            cell.alignment = Alignment(
                vertical="top", wrap_text=True
            )

            if row_number % 2 == 1:
                cell.fill = PatternFill(
                    "solid", fgColor="EDF3F8"
                )

            if column in formats:
                cell.number_format = formats[column]

        sheet.row_dimensions[row_number].height = 45

    for column, width in enumerate(widths, start=1):
        letter = get_column_letter(column)
        sheet.column_dimensions[letter].width = width

    last_column = get_column_letter(column_count)
    last_row = max(4, sheet.max_row)

    sheet.freeze_panes = "A5"
    sheet.auto_filter.ref = f"A4:{last_column}{last_row}"
    sheet.print_title_rows = "1:4"
    sheet.oddFooter.center.text = "Page &P of &N"
    sheet.oddFooter.center.size = 10
    sheet.oddFooter.left.text = title
    sheet.oddFooter.left.size = 9
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0

    if not rows:
        sheet.cell(5, 1, "No records yet.")

def style_summary(sheet, start_row, row_count, row_height=32):
    for row in range(start_row, start_row + row_count):
        sheet.row_dimensions[row].height = row_height

        for column in (3, 4):
            cell = sheet.cell(row, column)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="EDF3F8")
            cell.alignment = Alignment(
                vertical="center", wrap_text=True
            )
   
    sheet.print_area = f"A1:{get_column_letter(sheet.max_column)}{start_row + row_count - 1}"

def build_overview(sheet, vehicle, service_cost, missing_costs, fuel_cost, gallons):
    """Export the app's overview as a readable snapshot of the selected vehicle."""
    sheet.sheet_view.showGridLines = False
    for column, width in zip("ABCD", (29, 23, 27, 15)):
        sheet.column_dimensions[column].width = width
    sheet.merge_cells("A1:D1")
    sheet["A1"] = f"{vehicle.year} {vehicle.name} — Overview"
    sheet["A1"].data_type = "s"
    sheet["A1"].font = Font(name="Calibri", size=18, bold=True, color="FFFFFF")
    sheet["A1"].fill = PatternFill("solid", fgColor="17365D")
    sheet.row_dimensions[1].height = 36
    sheet.merge_cells("A2:D2")
    sheet["A2"] = f"Exported {date.today():%m/%d/%Y}"
    sheet["A2"].font = Font(name="Calibri", size=10, color="666666")

    def section(row, title):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = sheet.cell(row, 1, title)
        cell.font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="245A81")
        sheet.row_dimensions[row].height = 26

    def metric(row, label, value, number_format=None):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        sheet.cell(row, 1, label)
        sheet.merge_cells(start_row=row, start_column=3, end_row=row, end_column=4)
        cell = sheet.cell(row, 3, value)
        if number_format:
            cell.number_format = number_format
        for column in (1, 3):
            target = sheet.cell(row, column)
            if isinstance(target.value, str):
                target.data_type = "s"
            target.font = Font(name="Calibri", size=11)
            target.alignment = Alignment(vertical="center", wrap_text=True)
            if row % 2 == 0:
                target.fill = PatternFill("solid", fgColor="EDF3F8")
        sheet.row_dimensions[row].height = 24

    def note(row, text):
        sheet.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
        cell = sheet.cell(row, 1, text)
        cell.font = Font(name="Calibri", size=10, italic=True, color="666666")
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.row_dimensions[row].height = 32

    def status(remaining):
        if remaining < 0:
            return f"OVERDUE by {abs(remaining):,} miles"
        if remaining == 0:
            return "DUE NOW"
        return f"{remaining:,} miles remaining"

    section(4, "VEHICLE")
    metric(5, "Vehicle", vehicle.name)
    metric(6, "Model year", vehicle.year, "0")
    metric(7, "Current odometer (mi)", vehicle.mileage, "#,##0")
    section(9, "MAINTENANCE")
    metric(10, "Oil change", status(vehicle.next_service() - vehicle.mileage))
    tire_status = "Last rotation unknown" if vehicle.last_tire_rotation_mileage is None else status(
        vehicle.last_tire_rotation_mileage + vehicle.tire_rotation_interval - vehicle.mileage)
    metric(11, "Tire rotation", tire_status)
    section(13, "TIRE PRESSURE")
    for column, title in enumerate(("Tire", "Starting PSI", "Current PSI", "Unit"), start=1):
        cell = sheet.cell(14, column, title)
        cell.font = Font(name="Calibri", bold=True)
        cell.fill = PatternFill("solid", fgColor="EDF3F8")
        cell.alignment = Alignment(horizontal="left" if column == 1 else "center", vertical="center", wrap_text=True)
    sheet.row_dimensions[14].height = 26
    starting = getattr(vehicle, "starting_tire_pressures", vehicle.tire_pressures)
    for row, (key, label) in enumerate((
        ("driver_front", "Driver's front"), ("driver_rear", "Driver's rear"),
        ("passenger_front", "Passenger front"), ("passenger_rear", "Passenger rear")
    ), start=15):
        values = (label, starting.get(key), vehicle.tire_pressures.get(key), "PSI")
        for column, value in enumerate(values, start=1):
            cell = sheet.cell(row, column, "Not recorded" if value is None else value)
            cell.font = Font(name="Calibri", size=11)
            cell.alignment = Alignment(horizontal="left" if column == 1 else "center", vertical="center", wrap_text=True)
            if column in (2, 3) and value is not None:
                cell.number_format = "0.00"
            if row % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="EDF3F8")
        sheet.row_dimensions[row].height = 24
    note(19, "Current PSI is calculated from recorded starting pressure and added PSI. Verify with a tire gauge.")
    section(21, "SERVICE")
    metric(22, "Service records", len(vehicle.service_history), "0")
    metric(23, "Recorded spending", service_cost, '\"$\"#,##0.00')
    metric(24, "Records without a cost", missing_costs, "0")
    note(25, "Missing costs are excluded from spending.")
    section(27, "FUEL")
    metric(28, "Fill-ups", len(vehicle.fuel_history), "0")
    metric(29, "Total fuel (US gallons)", gallons, "0.000")
    metric(30, "Total spending", fuel_cost, '\"$\"#,##0.00')
    metric(31, "Average price per gallon", fuel_cost / gallons if gallons > 0 else "Not available", '\"$\"0.000')
    sheet.freeze_panes = "A5"
    section(33, "BATTERY")
    note(34, battery_summary(vehicle))
    sheet.row_dimensions[34].height = 62
    sheet.print_area = "A1:D34"
    sheet.print_options.horizontalCentered = True
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    sheet.page_setup.orientation = "portrait"
    sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 1
    sheet.oddFooter.center.text = "Page &P of &N"
    sheet.oddFooter.left.text = "Vehicle Overview"


def export_vehicle_excel(vehicle, output_file=None):
    if output_file is None:
        safe_name = "".join(
            character if character.isalnum() else "_"
            for character in vehicle.name
        ).strip("_") or "vehicle"

        folder = Path(__file__).parent / "exports"
        output_file = folder / f"{vehicle.year}_{safe_name}.xlsx"

        if output_file.exists():
            confirm = input(
                f"{output_file.name} already exists. "
                "Replace it? (yes/no): "
            ).strip().lower()

            if confirm != "yes":
                print("Export canceled.")
                return

    output_file = Path(output_file)
    folder = output_file.parent

    workbook = Workbook()
    overview_sheet = workbook.active
    overview_sheet.title = "Overview"
    service_sheet = workbook.create_sheet("Service History")
    fuel_sheet = workbook.create_sheet("Fuel History")

    service_rows = []
    total_service_cost = Decimal("0")
    missing_service_cost = 0

    for record in vehicle.service_history:
        cents = record.get("cost_cents")
        if cents is not None:
            total_service_cost += Decimal(cents) / 100
        else:
            missing_service_cost += 1

        cost = (
            Decimal(cents) / 100
            if cents is not None
            else "Not recorded"
        )

        service_rows.append([
            date.fromisoformat(record["date"]),
            record["mileage"],
            record["description"],
            cost,
            (
                "Yes" if record["oil_reset"] else "No"
            ) if "oil_reset" in record else "Unknown",
            (
                "Yes" if record["tire_reset"] else "No"
            ) if "tire_reset" in record else "Unknown"
        ])

    total_fuel_cost = Decimal("0")
    total_gallons = Decimal("0")

     
    fuel_rows = []
    previous_full_mileage = None
    gallons_since_full = Decimal("0")

    for record in vehicle.fuel_history:
        gallons = Decimal(record["gallons"])
        total_gallons += gallons
        cost = Decimal(record["cost_cents"]) / 100
        total_fuel_cost += cost
        mpg = None

        if previous_full_mileage is not None:
            gallons_since_full += gallons

        if record["full_tank"]:
            if previous_full_mileage is not None:
                miles_driven = record["mileage"] - previous_full_mileage
                mpg = Decimal(miles_driven) / gallons_since_full

            previous_full_mileage = record["mileage"]
            gallons_since_full = Decimal("0")

        fuel_rows.append([
            date.fromisoformat(record["date"]),
            record["mileage"],
            gallons,
            cost,
            "Yes" if record["full_tank"] else "No",
            mpg,
            cost / gallons
        ])

    title = f"{vehicle.year} {vehicle.name}"

    style_sheet(
        service_sheet,
        f"{title} — Service History",
        [
            "Service Date", "Odometer (mi)", "Service Performed",
            "Cost", "Oil Reset", "Tire Reset"
        ],
        service_rows,
        [16, 19, 55, 18, 16, 16],
        {1: "mm/dd/yyyy", 2: "#,##0", 4: '"$"#,##0.00'}
    )

    style_sheet(
        fuel_sheet,
        f"{title} — Fuel History",
                [
            "Fill-up Date", "Odometer (mi)", "US Gallons",
            "Total Cost", "Full Tank", "-MPG", "Price/Gallon"
        ],
                fuel_rows,
        [18, 21, 19, 20, 18, 14, 18],
        {
            1: "mm/dd/yyyy",
            2: "#,##0",
            3: "0.000",
            4: '"$"#,##0.00',
            6: "0.00",
            7: '"$"0.000'
        }
    )
    
    service_with_cost = len(service_rows) - missing_service_cost

    if service_with_cost > 0:
        average_service_cost = total_service_cost / service_with_cost
    else:
        average_service_cost = None
 
    service_summary_row = service_sheet.max_row + 2
    service_sheet.cell(service_summary_row, 3, "Total recorded service spending")
    service_sheet.cell(service_summary_row, 4, total_service_cost)
    service_sheet.cell(service_summary_row, 4).number_format = '"$"#,##0.00'    
    service_sheet.cell(service_summary_row +1, 3, "Services with no cost recorded")
    service_sheet.cell(service_summary_row + 1, 4,  missing_service_cost)    
    service_sheet.cell(service_summary_row +2, 3, "Service records")
    service_sheet.cell(service_summary_row +2, 4, len(service_rows))   
    service_sheet.cell(service_summary_row +3, 3, "Average recorded service cost")
    service_sheet.cell(service_summary_row +3, 4, average_service_cost)   
    service_sheet.cell(service_summary_row +3, 4).number_format = '"$"#,##0.00'
    
    style_summary(service_sheet, service_summary_row, 4)
            
    summary_row = fuel_sheet.max_row + 2
    fuel_sheet.cell(summary_row, 3, "Total fuel spending")
    fuel_sheet.cell(summary_row, 4, total_fuel_cost)
    fuel_sheet.cell(summary_row, 4).number_format = '"$"#,##0.00'
    fuel_sheet.cell(summary_row +1, 3, "Total gallons")
    fuel_sheet.cell(summary_row +1, 4, total_gallons)
    fuel_sheet.cell(summary_row +1, 4).number_format = "0.000"
    average_price = total_fuel_cost / total_gallons if total_gallons > 0 else None
    fuel_sheet.cell(summary_row +2, 3, "Average price/gallon")
    fuel_sheet.cell(summary_row +2, 4, average_price)
    fuel_sheet.cell(summary_row +2, 4).number_format = '"$"0.000'
    fuel_sheet.cell(summary_row + 3, 3, "Fill-ups")
    fuel_sheet.cell(summary_row + 3, 4, len(fuel_rows))

    style_summary(fuel_sheet, summary_row, 4, row_height=40)

    build_overview(overview_sheet, vehicle, total_service_cost, missing_service_cost,
                   total_fuel_cost, total_gallons)

    try:
        folder.mkdir(exist_ok=True)
        workbook.save(output_file)
        print(f"Excel workbook exported to:\n{output_file}")
        return output_file

    except OSError as error:
        print(f"Could not export workbook: {error}")
        print("Close the workbook in Excel and try again.")

        return None

    finally:
        workbook.close()