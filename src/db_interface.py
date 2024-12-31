import os
from typing import List, Tuple
from dotenv import load_dotenv
import psycopg2
from psycopg2 import OperationalError


class DBInterface:
    def __init__(self):
        self.conn = self.create_connection()
        if not self.conn:
            raise Exception("Could not connect to database")

    def create_connection(self):
        load_dotenv()
        try:
            connection = psycopg2.connect(
                dbname="sidb",
                user=os.getenv("DB_USER"),
                password=os.getenv("DB_PASS"),
                host=os.getenv("DB_HOST"),
                port="5432"
            )
            return connection
        except OperationalError:
            return None

    def execute_query(self, query, params=None) -> List[Tuple]:
        try:
            cursor = self.conn.cursor()
            if params:
                cursor.execute(query, str(params))
            else:
                cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
            return results
        except Exception as e:
            print(f"Database query failed: {e}")
            raise e

    def get_contexts(self):
        return self.execute_query(
            "SELECT context_id, context_name FROM contexts;"
        )

    def get_groups(self, context_id:int):
        return self.execute_query(
            f"SELECT group_id, group_name FROM groups WHERE context_id = {context_id};",
            
        )
    
    def get_datasets(self, context_id:int):
        return self.execute_query(
            f"SELECT dataset_id, dataset_name, unit FROM datasets WHERE context_id = {context_id};",
        )
    
    def get_data_for_table(
        self,
        context_id: int,
        group_ids: List[int],
        dataset_ids: List[int]
    ) -> List[Tuple]:
        """
        Returns rows of the form:
            (context_name, entity_id, entity_name,
            dataset_id, dataset_name, value)
        """
        if not group_ids or not dataset_ids:
            return []

        group_placeholders   = ",".join(["%s"] * len(group_ids))
        dataset_placeholders = ",".join(["%s"] * len(dataset_ids))

        sql = f"""
        SELECT 
            c.context_name,
            e.entity_id,
            e.entity_name,
            d.dataset_id,
            d.dataset_name,
            dv.value
        FROM contexts c
            JOIN groups g      ON g.context_id  = c.context_id
            JOIN entities e    ON e.group_id    = g.group_id
            JOIN datavalues dv ON dv.entity_id  = e.entity_id
            JOIN datasets d    ON d.dataset_id  = dv.dataset_id
        WHERE c.context_id = %s
            AND g.group_id IN ({group_placeholders})
            AND d.dataset_id IN ({dataset_placeholders})
        ORDER BY e.entity_name, d.dataset_name;
        """

        params = [context_id] + group_ids + dataset_ids

        cursor = self.conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        return rows

    def get_citation(self, dataset_id: int):
        citation = self.execute_query(
            f"SELECT text, author, url, start_date, end_date, date_accessed FROM citations WHERE dataset_id = {dataset_id};"
        )
        if not citation:
            return None
        return {
            "text": citation[0][0],
            "author": citation[0][1],
            "url": citation[0][2],
            "start_date": citation[0][3],
            "end_date": citation[0][4],
            "date_accessed": citation[0][5]
        }