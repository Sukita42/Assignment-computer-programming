"""
Car Rental Management (Minimal, OOP, Terminal)
"""

import struct, os, sys, textwrap
from datetime import datetime, date
from typing import Optional, List, Iterable

# ----------------------
# Utilities for fixed-length utf-8 fields
# ----------------------
def fixed_bytes(s: str, length: int) -> bytes:
    """Encode string to utf-8, truncate or pad with spaces to exact byte length."""
    b = (s or '').encode('utf-8')[:length]
    return b + b' ' * (length - len(b))

def bytes_to_str(b: bytes) -> str:
    return b.rstrip(b' ').decode('utf-8', errors='ignore')

# ----------------------
# Record formats (little-endian)
# ----------------------
# Car:
# car_id(10), plate_no(10), brand(20), model(30), year(uint32), price(double), status(10), rented(3)
CAR_STRUCT_FMT = '<10s10s20s30sId10s3s'
CAR_RECORD_SIZE = struct.calcsize(CAR_STRUCT_FMT)

# Customer:
# cust_id(10), name(50), id_card(13), phone(15), email(50)
CUST_STRUCT_FMT = '<10s50s13s15s50s'
CUST_RECORD_SIZE = struct.calcsize(CUST_STRUCT_FMT)

# Contract:
# contract_id(10), car_id(10), cust_id(10), start_date(10), end_date(10), total_cost(double), status(10)
CONTRACT_STRUCT_FMT = '<10s10s10s10s10sd10s'
CONTRACT_RECORD_SIZE = struct.calcsize(CONTRACT_STRUCT_FMT)

# ----------------------
# Models
# ----------------------
class Car:
    def __init__(self, car_id, plate, brand, model, year, price_per_day, status='Active', rented='No'):
        self.car_id, self.plate, self.brand, self.model = car_id, plate, brand, model
        self.year, self.price_per_day, self.status, self.rented = year, price_per_day, status, rented

    def pack(self):
        return struct.pack(
            CAR_STRUCT_FMT,
            fixed_bytes(self.car_id,10),
            fixed_bytes(self.plate,10),
            fixed_bytes(self.brand,20),
            fixed_bytes(self.model,30),
            int(self.year),
            float(self.price_per_day),
            fixed_bytes(self.status,10),
            fixed_bytes(self.rented,3),
        )

    @classmethod
    def unpack(cls, b):
        f = struct.unpack(CAR_STRUCT_FMT, b)
        return cls(bytes_to_str(f[0]),bytes_to_str(f[1]),bytes_to_str(f[2]),bytes_to_str(f[3]),int(f[4]),float(f[5]),bytes_to_str(f[6]),bytes_to_str(f[7]))

class Customer:
    def __init__(self, cust_id, name, id_card, phone, email):
        self.cust_id, self.name, self.id_card, self.phone, self.email = cust_id, name, id_card, phone, email

    def pack(self) -> bytes:
        return struct.pack(
            CUST_STRUCT_FMT,
            fixed_bytes(self.cust_id,10),
            fixed_bytes(self.name,50),
            fixed_bytes(self.id_card,13),
            fixed_bytes(self.phone,15),
            fixed_bytes(self.email,50),
        )

    @classmethod
    def unpack(cls, b):
        f = struct.unpack(CUST_STRUCT_FMT, b)
        return cls(bytes_to_str(f[0]),bytes_to_str(f[1]),bytes_to_str(f[2]),bytes_to_str(f[3]),bytes_to_str(f[4]))

class Contract:
    def __init__(self, contract_id, car_id, cust_id, start_date, end_date, total_cost=0.0, status='active'):
        self.contract_id, self.car_id, self.cust_id = contract_id, car_id, cust_id
        self.start_date, self.end_date, self.total_cost, self.status = start_date, end_date, float(total_cost), status

    def pack(self) -> bytes:
        return struct.pack(
            CONTRACT_STRUCT_FMT,
            fixed_bytes(self.contract_id,10),
            fixed_bytes(self.car_id,10),
            fixed_bytes(self.cust_id,10),
            fixed_bytes(self.start_date,10),
            fixed_bytes(self.end_date,10),
            float(self.total_cost),
            fixed_bytes(self.status,10),
        )

    @classmethod
    def unpack(cls, b):
        f = struct.unpack(CONTRACT_STRUCT_FMT, b)
        return cls(bytes_to_str(f[0]),bytes_to_str(f[1]),bytes_to_str(f[2]),bytes_to_str(f[3]),bytes_to_str(f[4]),float(f[5]),bytes_to_str(f[6]))

# ----------------------
# Repositories (file access)
# ----------------------
class BinaryRepository:
    def __init__(self, filename, record_size):
        self.filename, self.recsize = filename, record_size
        # ensure file exists
        if not os.path.exists(self.filename):
            open(self.filename, 'ab').close()

    def iterate_raw(self):
        with open(self.filename, 'rb') as f:
            while True:
                b = f.read(self.recsize)
                if not b or len(b) < self.recsize: break
                yield b

    def read_all_raw(self): return list(self.iterate_raw())

    def overwrite_all_raw(self, records):
        tmp = self.filename + '.tmp'
        with open(tmp, 'wb') as f:
            for r in records: f.write(r)
        os.replace(tmp, self.filename)

class CarRepository(BinaryRepository):
    def __init__(self, filename='cars.dat'): super().__init__(filename, CAR_RECORD_SIZE)
    def all(self): return [Car.unpack(b) for b in self.iterate_raw()]
    def find(self, car_id): return next((c for c in self.all() if c.car_id == car_id), None)
    def add(self, car):
        if self.find(car.car_id): return False
        with open(self.filename, 'ab') as f: f.write(car.pack())
        return True
    def update(self, car_id, new_car):
        raw, changed, out = self.read_all_raw(), False, []
        for b in raw:
            c = Car.unpack(b)
            if c.car_id == car_id: out.append(new_car.pack()); changed = True
            else: out.append(b)
        if changed: self.overwrite_all_raw(out)
        return changed
    def mark_deleted(self, car_id):
        raw, changed, out = self.read_all_raw(), False, []
        for b in raw:
            c = Car.unpack(b)
            if c.car_id == car_id: c.status = 'Deleted'; out.append(c.pack()); changed = True
            else: out.append(b)
        if changed: self.overwrite_all_raw(out)
        return changed

class CustomerRepository(BinaryRepository):
    def __init__(self, filename='customers.dat'): super().__init__(filename, CUST_RECORD_SIZE)
    def all(self): return [Customer.unpack(b) for b in self.iterate_raw()]
    def find(self, cust_id): return next((c for c in self.all() if c.cust_id == cust_id), None)
    def add(self, cust):
        if self.find(cust.cust_id): return False
        with open(self.filename, 'ab') as f: f.write(cust.pack())
        return True
    def update(self, cust_id, new_cust):
        raw, changed, out = self.read_all_raw(), False, []
        for b in raw:
            c = Customer.unpack(b)
            if c.cust_id == cust_id: out.append(new_cust.pack()); changed = True
            else: out.append(b)
        if changed: self.overwrite_all_raw(out)
        return changed

class ContractRepository(BinaryRepository):
    def __init__(self, filename='contracts.dat'): super().__init__(filename, CONTRACT_RECORD_SIZE)
    def all(self): return [Contract.unpack(b) for b in self.iterate_raw()]
    def find(self, contract_id): return next((c for c in self.all() if c.contract_id == contract_id), None)
    def add(self, contract):
        if self.find(contract.contract_id): return False
        with open(self.filename, 'ab') as f: f.write(contract.pack())
        return True
    def update(self, contract_id, new_contract):
        raw, changed, out = self.read_all_raw(), False, []
        for b in raw:
            c = Contract.unpack(b)
            if c.contract_id == contract_id: out.append(new_contract.pack()); changed = True
            else: out.append(b)
        if changed: self.overwrite_all_raw(out)
        return changed

# ----------------------
# Business logic / CLI
# ----------------------
def input_nonempty(prompt, max_len=None):
    while True:
        v = input(prompt).strip()
        if not v: print("ระบุค่า (ห้ามว่าง)."); continue
        if max_len and len(v.encode('utf-8')) > max_len:
            print(f"ข้อมูลยาวเกิน (byte) มากกว่า {max_len}, กรุณาลดความยาว."); continue
        return v

def parse_date(s): return datetime.strptime(s, '%Y-%m-%d').date()
def date_diff_days(a, b): return max(0, (parse_date(b) - parse_date(a)).days + 1)

def generate_customer_contracts_report(filename='customer_contracts_report.txt'):
    customers = CustomerRepository().all()
    contracts = ContractRepository().all()
    cars = CarRepository().all()
    car_dict = {c.car_id: c for c in cars}
    with open(filename, 'w', encoding='utf-8') as f:
        for cust in customers:
            cust_contracts = [ct for ct in contracts if ct.cust_id == cust.cust_id]
            f.write(f"Customer: {cust.cust_id} {cust.name}\n")
            if not cust_contracts:
                f.write("  No contracts found.\n\n"); continue
            f.write(f"  {'ContractID':<10} {'CarID':<10} {'Car':<20} {'Start':<10} {'End':<10} {'Total':>10} {'Status':<10}\n")
            for ct in cust_contracts:
                car = car_dict.get(ct.car_id)
                car_name = f"{car.brand} {car.model}" if car else ct.car_id
                f.write(f"  {ct.contract_id:<10} {ct.car_id:<10} {car_name:<20} {ct.start_date:<10} {ct.end_date:<10} {ct.total_cost:>10.2f} {ct.status:<10}\n")
            f.write(f"  Total contracts: {len(cust_contracts)}\n\n")
    print(f'Report generated: {filename}')

# ----------------------
# Menu and operations
# ----------------------
def menu():
    cars = CarRepository()
    customers = CustomerRepository()
    contracts = ContractRepository()

    def add_car():
        print("--- Add Car ---")
        car_id = input_nonempty("Car ID (<=10 chars): ", 10)
        if cars.find(car_id):
            print("มี car_id นี้แล้ว.")
            return
        plate = input_nonempty("Plate No (<=10): ", 10)
        brand = input_nonempty("Brand (<=20): ", 20)
        model = input_nonempty("Model (<=30): ", 30)
        year_s = input_nonempty("Year (YYYY): ", 4)
        try:
            year = int(year_s)
        except ValueError:
            print("ปีไม่ถูกต้อง.")
            return
        price_s = input_nonempty("Price per day (THB): ")
        try:
            price = float(price_s)
        except ValueError:
            print("กรุณาใส่ตัวเลข.")
            return
        car = Car(car_id=car_id, plate=plate, brand=brand, model=model, year=year, price_per_day=price)
        if cars.add(car):
            print("เพิ่มรถเรียบร้อย.")
        else:
            print("เพิ่มไม่สำเร็จ (ซ้ำ).")

    def update_car():
        print("--- Update Car ---")
        car_id = input_nonempty("Car ID to update: ", 10)
        c = cars.find(car_id)
        if not c:
            print("ไม่พบรถนี้.")
            return
        print("Leave blank จะเก็บค่าเดิม")
        plate = input(f"Plate [{c.plate}]: ").strip() or c.plate
        brand = input(f"Brand [{c.brand}]: ").strip() or c.brand
        model = input(f"Model [{c.model}]: ").strip() or c.model
        year_in = input(f"Year [{c.year}]: ").strip()
        year = int(year_in) if year_in else c.year
        price_in = input(f"Price [{c.price_per_day}]: ").strip()
        price = float(price_in) if price_in else c.price_per_day
        status = input(f"Status [{c.status}]: ").strip() or c.status
        rented = input(f"Rented (Yes/No) [{c.rented}]: ").strip() or c.rented
        newcar = Car(car_id=car_id, plate=plate, brand=brand, model=model, year=year, price_per_day=price, status=status, rented=rented)
        if cars.update(car_id, newcar):
            print("อัปเดตเรียบร้อย.")
        else:
            print("ไม่พบหรืออัปเดตไม่สำเร็จ.")

    def delete_car():
        print("--- Delete Car (mark Deleted) ---")
        car_id = input_nonempty("Car ID to delete: ", 10)
        if cars.mark_deleted(car_id):
            print("ทำเครื่องหมาย Deleted เรียบร้อย.")
        else:
            print("ไม่พบ car_id.")

    def view_car():
        print("--- View Car ---")
        print("1) ดูรายการทั้งหมด\n2) ดูรายการเดียว\n3) ดูแบบกรอง (brand/status)\n4) สถิติโดยสรุป\n")
        sub = input("เลือก: ").strip()
        if sub == '1':
            allc = cars.all()
            print_table_cars(allc)
        elif sub == '2':
            cid = input_nonempty("Car ID: ", 10)
            c = cars.find(cid)
            if c:
                print_table_cars([c])
            else:
                print("ไม่พบ.")
        elif sub == '3':
            brand = input("Brand (leave blank = any): ").strip()
            status = input("Status (Active/Deleted) (leave blank = any): ").strip()
            filtered = [c for c in cars.all() if (not brand or c.brand.lower() == brand.lower()) and (not status or c.status.lower() == status.lower())]
            print_table_cars(filtered)
        elif sub == '4':
            summary = cars_summary(cars.all())
            print(summary)
        else:
            print("Invalid.")

    def add_customer():
        print("--- Add Customer ---")
        cust_id = input_nonempty("Customer ID (<=10): ", 10)
        if customers.find(cust_id):
            print("มี cust_id นี้แล้ว.")
            return
        name = input_nonempty("Name (<=50): ", 50)
        id_card = input_nonempty("ID card (13 digits): ", 13)
        phone = input_nonempty("Phone (<=15): ", 15)
        email = input_nonempty("Email (<=50): ", 50)
        cust = Customer(cust_id=cust_id, name=name, id_card=id_card, phone=phone, email=email)
        if customers.add(cust):
            print("เพิ่มลูกค้าเรียบร้อย.")
        else:
            print("เพิ่มลูกค้าไม่สำเร็จ.")

    def update_customer():
        print("--- Update Customer ---")
        cid = input_nonempty("Customer ID to update: ", 10)
        c = customers.find(cid)
        if not c:
            print("ไม่พบลูกค้า.")
            return
        name = input(f"Name [{c.name}]: ").strip() or c.name
        id_card = input(f"ID card [{c.id_card}]: ").strip() or c.id_card
        phone = input(f"Phone [{c.phone}]: ").strip() or c.phone
        email = input(f"Email [{c.email}]: ").strip() or c.email
        newc = Customer(cust_id=cid, name=name, id_card=id_card, phone=phone, email=email)
        if customers.update(cid, newc):
            print("อัปเดตเรียบร้อย.")
        else:
            print("ไม่สำเร็จ.")

    def delete_customer():
        print("--- Delete Customer (physically remove) ---")
        cid = input_nonempty("Customer ID to delete: ", 10)
        raw = customers.read_all_raw()
        out = []
        found = False
        for b in raw:
            c = Customer.unpack(b)
            if c.cust_id == cid:
                found = True
                continue
            out.append(b)
        if found:
            customers.overwrite_all_raw(out)
            print("ลบลูกค้าเรียบร้อย.")
        else:
            print("ไม่พบ.")

    def view_customer():
        print("--- View Customer ---")
        print("1) ดูทั้งหมด\n2) ดูลูกค้ารายเดียว\n")
        sub = input("เลือก: ").strip()
        if sub == '1':
            allc = customers.all()
            print_table_customers(allc)
        elif sub == '2':
            cid = input_nonempty("Customer ID: ", 10)
            c = customers.find(cid)
            if c:
                print_table_customers([c])
            else:
                print("ไม่พบ.")
        else:
            print("Invalid.")

    def add_contract():
        print("--- Add Contract ---")
        contract_id = input_nonempty("Contract ID (<=10): ", 10)
        if contracts.find(contract_id):
            print("มี contract_id นี้แล้ว.")
            return
        car_id = input_nonempty("Car ID: ", 10)
        car = cars.find(car_id)
        if not car or car.status.lower() == 'deleted':
            print("ไม่พบรถหรือรถถูกลบ.")
            return
        if car.rented.lower() == 'yes':
            print("รถไม่ว่าง.")
            return
        cust_id = input_nonempty("Customer ID: ", 10)
        cust = customers.find(cust_id)
        if not cust:
            print("ไม่พบลูกค้า.")
            return
        start = input_nonempty("Start date (YYYY-MM-DD): ", 10)
        end = input_nonempty("End date (YYYY-MM-DD): ", 10)
        try:
            dcount = date_diff_days(start, end)
        except Exception:
            print("รูปแบบวันที่ไม่ถูกต้อง.")
            return
        est_cost = dcount * car.price_per_day
        print(f"Estimated days: {dcount}, Estimated cost: {est_cost:.2f} THB")
        confirm = input("Confirm create contract? (y/n): ").strip().lower()
        if confirm != 'y':
            print("ยกเลิก.")
            return
        contract = Contract(contract_id=contract_id, car_id=car_id, cust_id=cust_id, start_date=start, end_date=end, total_cost=est_cost, status='active')
        if contracts.add(contract):
            # update car rented status
            car.rented = 'Yes'
            cars.update(car_id, car)
            print("สร้างสัญญาเรียบร้อย.")
        else:
            print("ไม่สำเร็จ.")

    def close_contract():
        print("--- Close Contract ---")
        cid = input_nonempty("Contract ID: ", 10)
        c = contracts.find(cid)
        if not c:
            print("ไม่พบสัญญา.")
            return
        if c.status.lower() == 'closed':
            print("สัญญาปิดแล้ว.")
            return
        # compute actual cost using current date or use recorded end_date
        actual_end = input(f"Actual return date (YYYY-MM-DD) [{c.end_date}]: ").strip() or c.end_date
        try:
            days = date_diff_days(c.start_date, actual_end)
        except Exception:
            print("วันที่ไม่ถูกต้อง.")
            return
        # find car price
        car = cars.find(c.car_id)
        if not car:
            print("ไม่พบรถที่เกี่ยวข้อง.")
            return
        actual_cost = days * car.price_per_day
        c.total_cost = actual_cost
        c.end_date = actual_end
        c.status = 'closed'
        if contracts.update(cid, c):
            # update car rented flag
            car.rented = 'No'
            cars.update(car.car_id, car)
            print(f"สัญญาปิดแล้ว, Total cost: {actual_cost:.2f}")
        else:
            print("ปิดสัญญาไม่สำเร็จ.")

    def view_contract():
        print("--- View Contract ---")
        print("1) View all\n2) View one\n3) View active/closed\n")
        sub = input("เลือก: ").strip()
        if sub == '1':
            allc = contracts.all()
            print_table_contracts(allc)
        elif sub == '2':
            cid = input_nonempty("Contract ID: ", 10)
            c = contracts.find(cid)
            if c:
                print_table_contracts([c])
            else:
                print("ไม่พบ.")
        elif sub == '3':
            st = input("Status (active/closed): ").strip().lower()
            filtered = [c for c in contracts.all() if c.status.lower() == st]
            print_table_contracts(filtered)
        else:
            print("Invalid.")

    def generate_report():
        print("Generating report.txt ...")
        make_report(cars.all(), customers.all(), contracts.all())
        print("Generated report.txt")

    # Main menu loop
    while True:
        print(textwrap.dedent("""
        === Car Rental Management ===
        1) Car Management
        2) Customer Management
        3) Contract Management
        4) Generate Report (report.txt)
        0) Exit
        """))
        choice = input("Select: ").strip()
        try:
            if choice == '1':
                print(textwrap.dedent("""
                --- Car Management ---
                1) Add Car
                2) Update Car
                3) Delete Car
                4) View Cars
                0) Back
                """))
                sub = input("Select: ").strip()
                if sub == '1':
                    add_car()
                elif sub == '2':
                    update_car()
                elif sub == '3':
                    delete_car()
                elif sub == '4':
                    view_car()
            elif choice == '2':
                print(textwrap.dedent("""
                --- Customer Management ---
                1) Add Customer
                2) Update Customer
                3) Delete Customer
                4) View Customers
                0) Back
                """))
                sub = input("Select: ").strip()
                if sub == '1':
                    add_customer()
                elif sub == '2':
                    update_customer()
                elif sub == '3':
                    delete_customer()
                elif sub == '4':
                    view_customer()
            elif choice == '3':
                print(textwrap.dedent("""
                --- Contract Management ---
                1) Add Contract
                2) Close Contract
                3) View Contracts
                0) Back
                """))
                sub = input("Select: ").strip()
                if sub == '1':
                    add_contract()
                elif sub == '2':
                    close_contract()
                elif sub == '3':
                    view_contract()
            elif choice == '4':
                generate_report()
            elif choice == '0':
                print("Bye.")
                break
            else:
                print("Invalid selection.")
        except KeyboardInterrupt:
            print("\nInterrupted. Returning to main menu.")
        except Exception as e:
            print("Error:", e)

# ----------------------
# Pretty Printing tables
# ----------------------
def print_table_cars(rows: List[Car]):
    heading = "| CarID     | Plate     | Brand               | Model                         | Year | Rate (THB/day) | Status    | Rented |"
    sep = "+" + "-"*10 + "+" + "-"*10 + "+" + "-"*21 + "+" + "-"*31 + "+" + "-"*6 + "+" + "-"*16 + "+" + "-"*11 + "+" + "-"*8 + "+"
    print("Car Rent System - Cars")
    print(sep)
    print(heading)
    print(sep)
    for c in rows:
        print(f"| {c.car_id:<9} | {c.plate:<9} | {c.brand:<19} | {c.model:<30} | {c.year:4d} | {c.price_per_day:14.2f} | {c.status:<9} | {c.rented:<6} |")
    print(sep)

def print_table_customers(rows: List[Customer]):
    print("Customers")
    sep = "+" + "-"*10 + "+" + "-"*52 + "+" + "-"*15 + "+" + "-"*17 + "+" + "-"*52 + "+"
    print(sep)
    print("| CustID    | Name                                               | ID Card       | Phone           | Email                                              |")
    print(sep)
    for c in rows:
        print(f"| {c.cust_id:<9} | {c.name:<51} | {c.id_card:<13} | {c.phone:<15} | {c.email:<50} |")
    print(sep)

def print_table_contracts(rows: List[Contract]):
    print("Contracts")
    sep = "+" + "-"*11 + "+" + "-"*11 + "+" + "-"*11 + "+" + "-"*12 + "+" + "-"*12 + "+" + "-"*14 + "+" + "-"*10 + "+"
    print(sep)
    print("| ContractID | CarID      | CustID     | Start Date  | End Date    | Total Cost    | Status    |")
    print(sep)
    for c in rows:
        print(f"| {c.contract_id:<10} | {c.car_id:<10} | {c.cust_id:<10} | {c.start_date:<10} | {c.end_date:<10} | {c.total_cost:12.2f} | {c.status:<8} |")
    print(sep)

def cars_summary(allcars: List[Car]) -> str:
    total = len(allcars)
    active = [c for c in allcars if c.status.lower() == 'active']
    deleted = [c for c in allcars if c.status.lower() == 'deleted']
    rented = [c for c in active if c.rented.lower() == 'yes']
    available = [c for c in active if c.rented.lower() != 'yes']
    stats = []
    stats.append(f"Total Cars (records): {total}")
    stats.append(f"Active Cars         : {len(active)}")
    stats.append(f"Deleted Cars        : {len(deleted)}")
    stats.append(f"Currently Rented    : {len(rented)}")
    stats.append(f"Available Now       : {len(available)}")
    rates = [c.price_per_day for c in active]
    if rates:
        stats.append(f"Rate Min: {min(rates):.2f}")
        stats.append(f"Rate Max: {max(rates):.2f}")
        stats.append(f"Rate Avg: {sum(rates)/len(rates):.2f}")
    return "\n".join(stats)

# ----------------------
# Report generation
# ----------------------
def make_report(cars_list: List[Car], customers_list: List[Customer], contracts_list: List[Contract], filename: str = 'report.txt'):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    lines = []
    lines.append("Car Rent System - Summary Report (Sample)")
    lines.append(f"Generated At : {now}")
    lines.append("App Version  : 1.0")
    lines.append("Endianness   : Little-Endian")
    lines.append("Encoding     : UTF-8 (fixed-length)")
    lines.append("")
    # Header table
    lines.append("+" + "-"*10 + "+" + "-"*11 + "+" + "-"*21 + "+" + "-"*31 + "+" + "-"*6 + "+" + "-"*16 + "+" + "-"*11 + "+" + "-"*9 + "+")
    lines.append("| CarID     | Plate     | Brand               | Model                         | Year | Rate (THB/day) | Status    | Rented |")
    lines.append("+" + "-"*10 + "+" + "-"*11 + "+" + "-"*21 + "+" + "-"*31 + "+" + "-"*6 + "+" + "-"*16 + "+" + "-"*11 + "+" + "-"*9 + "+")
    for c in cars_list:
        lines.append(f"| {c.car_id:<9} | {c.plate:<9} | {c.brand:<19} | {c.model:<30} | {c.year:4d} | {c.price_per_day:14.2f} | {c.status:<9} | {c.rented:<6} |")
    lines.append("+" + "-"*10 + "+" + "-"*11 + "+" + "-"*21 + "+" + "-"*31 + "+" + "-"*6 + "+" + "-"*16 + "+" + "-"*11 + "+" + "-"*9 + "+")
    # Summary (active only)
    active = [c for c in cars_list if c.status.lower() == 'active']
    total = len(cars_list)
    deleted = len([c for c in cars_list if c.status.lower() == 'deleted'])
    currently_rented = len([c for c in active if c.rented.lower() == 'yes'])
    available = len([c for c in active if c.rented.lower() != 'yes'])
    lines.append("")
    lines.append("Summary (นับเฉพาะรถสถานะ Active)")
    lines.append(f"- Total Cars (records) : {total}")
    lines.append(f"- Active Cars          : {len(active)}")
    lines.append(f"- Deleted Cars         : {deleted}")
    lines.append(f"- Currently Rented     : {currently_rented}")
    lines.append(f"- Available Now        : {available}")
    lines.append("")
    # Rate stats
    rates = [c.price_per_day for c in active]
    lines.append("Rate Statistics (THB/day, Active only)")
    if rates:
        lines.append(f"- Min : {min(rates):.2f}")
        lines.append(f"- Max : {max(rates):.2f}")
        lines.append(f"- Avg : {sum(rates)/len(rates):.2f}")
    else:
        lines.append("- No active cars")
    lines.append("")
    # Cars by Brand
    lines.append("Cars by Brand (Active only)")
    brand_count = {}
    for c in active:
        brand_count[c.brand] = brand_count.get(c.brand, 0) + 1
    for k, v in sorted(brand_count.items(), key=lambda x: (-x[1], x[0])):
        lines.append(f"- {k} : {v}")
    lines.append("")
    # Contracts summary
    lines.append("Contracts Summary")
    lines.append(f"- Total Contracts: {len(contracts_list)}")
    active_contracts = [ct for ct in contracts_list if ct.status.lower() == 'active']
    closed_contracts = [ct for ct in contracts_list if ct.status.lower() == 'closed']
    lines.append(f"- Active Contracts: {len(active_contracts)}")
    total_revenue = sum(ct.total_cost for ct in closed_contracts)
    lines.append(f"- Total Revenue: {total_revenue:.2f} THB")
    lines.append("")
    # Write to file
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("\n".join(lines))
    return filename

# ----------------------
# Sample Data Generation
# ----------------------
def create_sample_data():
    cars = CarRepository()
    customers = CustomerRepository()
    contracts = ContractRepository()

    # Sample Cars
    sample_cars = [
        Car("C001", "กข 1234", "Toyota", "Camry", 2023, 2500.00),
        Car("C002", "งจ 5678", "Honda", "Civic", 2022, 2000.00),
        Car("C003", "ฟม 9012", "BMW", "320i", 2023, 3500.00),
        Car("C004", "พต 3456", "Toyota", "Yaris", 2022, 1500.00),
        Car("C005", "ลบ 7890", "Honda", "City", 2023, 1800.00),
        Car("C006", "รส 1122", "Mercedes", "C200", 2023, 4000.00),
    ]
    
    # Sample Customers
    sample_customers = [
        Customer("CUST001", "สมชาย ใจดี", "1234567890123", "081-234-5678", "somchai@email.com"),
        Customer("CUST002", "วันดี มีสุข", "2345678901234", "082-345-6789", "wandee@email.com"),
        Customer("CUST003", "มานะ รักเรียน", "3456789012345", "083-456-7890", "mana@email.com"),
    ]

    # First add cars and customers
    print("Adding sample data...")
    
    for car in sample_cars:
        if cars.add(car):
            print(f"Added car: {car.brand} {car.model}")
    
    for cust in sample_customers:
        if customers.add(cust):
            print(f"Added customer: {cust.name}")

    # Then add contracts and update car status
    sample_contracts = [
        Contract("CNT001", "C001", "CUST001", "2025-09-20", "2025-09-25", 12500.00, "closed"),
        Contract("CNT002", "C002", "CUST002", "2025-09-23", "2025-09-27", 8000.00, "active"),
        Contract("CNT003", "C003", "CUST003", "2025-09-15", "2025-09-22", 24500.00, "closed"),
    ]
    
    for contract in sample_contracts:
        # Update car rental status before adding contract
        car = cars.find(contract.car_id)
        if car:
            if contract.status.lower() == "active":
                car.rented = "Yes"
            else:
                car.rented = "No"
            cars.update(contract.car_id, car)
            print(f"Updated car {car.car_id} rental status to: {car.rented}")
        
        # Add the contract
        if contracts.add(contract):
            print(f"Added contract: {contract.contract_id}")

    print("Sample data added successfully!")

# ----------------------
# Entry point
# ----------------------
if __name__ == '__main__':
    # Basic creation of files if not exist handled by repositories
    try:
        # Ask if user wants to add sample data
        if not os.path.exists('cars.dat') and not os.path.exists('customers.dat') and not os.path.exists('contracts.dat'):
            print("\nไม่พบข้อมูลในระบบ ต้องการเพิ่มข้อมูลตัวอย่างหรือไม่? (y/n)")
            if input().strip().lower() == 'y':
                create_sample_data()
        menu()
    except KeyboardInterrupt:
        print("\nExit by user.")
        sys.exit(0)