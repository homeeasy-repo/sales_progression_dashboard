from datetime import datetime, date
import psycopg2
from dotenv import load_dotenv
import os
import csv
from collections import defaultdict

load_dotenv()

def get_todays_clients_excluding_may():
    try:
        db_url = os.getenv('DATABASE_URL')
        if not db_url:
            raise ValueError("DATABASE_URL not found in environment variables")

        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

      
        today = date.today().strftime('%Y-%m-%d')
        query = """
        SELECT 
            c.id,
            c.fullname,
            c.created,
            c.assigned_employee_name,
            c.source,
            c.stage,
            r.beds,
            r.baths,
            r.move_in_date,
            r.move_in_date_max,
            r.budget,
            r.budget_max,
            r.neighborhood
        FROM client c
        LEFT JOIN requirements r ON c.id = r.client_id 
        WHERE DATE(c.created) = %s
        AND (c.assigned_employee_name NOT ILIKE '%%may%%' OR c.assigned_employee_name IS NULL)
        ORDER BY c.created DESC
        """

        cursor.execute(query, (today,))
        results = cursor.fetchall()

        
        sales_rep_counts = defaultdict(int)
        for row in results:
            assigned_to = row[3] or 'Unassigned'
            sales_rep_counts[assigned_to] += 1

       
        os.makedirs('reports', exist_ok=True)
        
   
        filename = f'reports/daily_sales_report_{today}.csv'
        
        # Write to CSV file
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            csvwriter = csv.writer(csvfile)
            # Write headers
            headers = [
                'ID', 'Full Name', 'Created', 'Assigned To', 'Source', 'Stage',
                'Bedrooms', 'Bathrooms', 'Move In Date', 'Move In Date Max', 
                'Budget', 'Budget Max', 'Neighborhood'
            ]
            csvwriter.writerow(headers)
            
            # Write data rows
            for row in results:
                (client_id, fullname, created, assigned_to, source, stage,
                 beds, baths, move_in_date, move_in_date_max, budget,
                 budget_max, neighborhood) = row
                
                created_str = created.strftime('%Y-%m-%d %H:%M') if created else 'N/A'
                move_in_str = move_in_date.strftime('%Y-%m-%d') if move_in_date else 'N/A'
                move_in_max_str = move_in_date_max.strftime('%Y-%m-%d') if move_in_date_max else 'N/A'
                
                csvwriter.writerow([
                    client_id,
                    fullname or 'N/A',
                    created_str,
                    assigned_to or 'N/A',
                    source or 'N/A',
                    stage or 'N/A',
                    beds or 'N/A',
                    baths or 'N/A',
                    move_in_str,
                    move_in_max_str,
                    budget or 'N/A',
                    budget_max or 'N/A',
                    neighborhood or 'N/A'
                ])

            # Add empty row as separator
            csvwriter.writerow([])
            csvwriter.writerow(['Sales Rep Assignment Summary'])
            separator = '-' * 50
            csvwriter.writerow([separator])
            header = f"{'Sales Rep Name':<30} {'Number of Clients':<20}"
            csvwriter.writerow([header])
            csvwriter.writerow([separator])
            
            # Write sales rep summary with formatting
            for sales_rep, count in sorted(sales_rep_counts.items()):
                formatted_line = f"{sales_rep:<30} {count:<20}"
                csvwriter.writerow([formatted_line])

        if results:
            print(f"\nReport has been saved to: {filename}")
            print("\nClients and their requirements created today (excluding those assigned to May):")
            print("-" * 150)
            print(f"{'ID':<8} {'Full Name':<25} {'Created':<20} {'Assigned To':<20} "
                  f"{'Beds':<8} {'Baths':<8} {'Budget Range':<20} {'Move In':<12}")
            print("-" * 150)
            
            for row in results:
                (client_id, fullname, created, assigned_to, source, stage,
                 beds, baths, move_in_date, move_in_date_max, budget,
                 budget_max, neighborhood) = row
                
                created_str = created.strftime('%Y-%m-%d %H:%M') if created else 'N/A'
                move_in_str = move_in_date.strftime('%Y-%m-%d') if move_in_date else 'N/A'
                budget_range = f"${budget or 0:,} - ${budget_max or 0:,}" if budget or budget_max else 'N/A'
                
                print(f"{client_id:<8} {(fullname or 'N/A'):<25} {created_str:<20} "
                      f"{(assigned_to or 'N/A'):<20} {(str(beds) if beds else 'N/A'):<8} "
                      f"{(str(baths) if baths else 'N/A'):<8} {budget_range:<20} {move_in_str:<12}")

            # Print sales rep summary
            print("\nSales Rep Assignment Summary:")
            print("-" * 50)
            print(f"{'Sales Rep Name':<30} {'Number of Clients':<20}")
            print("-" * 50)
            for sales_rep, count in sorted(sales_rep_counts.items()):
                print(f"{sales_rep:<30} {count:<20}")
        else:
            print("\nNo clients found for today excluding those assigned to May.")

    except psycopg2.Error as e:
        print(f"Database error occurred: {e}")
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if 'conn' in locals() and conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    get_todays_clients_excluding_may()
