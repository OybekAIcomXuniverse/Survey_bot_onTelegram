#!/usr/bin/env python
# coding: utf-8

# In[ ]:


def general_pool():
    
    import sqlite3
    import pandas as pd
    import ast
    from pandas import ExcelWriter
    from io import BytesIO
    
    conn = sqlite3.connect('D:/Oybek/Python/Bot/Real sector/data/real_sector.db', check_same_thread=False)
    cursor = conn.cursor()
       
    def into_int(x):
        try:
            value = int(x)
            return value
        except:
            return x
        
    gen_cols = pd.Series(['user', 'user_name', 'language', 'time'])
    
    pool_list = ['manufacturing_pool', 'construction_pool', 'service_pool', 'retail_pool']
    
    df_list = []
    for i in pool_list:
        df = pd.read_sql_query(f'SELECT * FROM {i}', conn)
        df = df.fillna(0).applymap(into_int)
        questions_df = pd.read_csv(f'D:/Oybek/Python/Bot/Real sector/csv_files/{i[:i.index("_")]}_questions_uz.csv')
        df.columns = pd.concat([gen_cols, questions_df.question.drop_duplicates()])
        answer_df = questions_df[['answer_id', 'answer']].set_index('answer_id')
        
        def convert_answer(x):
            try:
                value = answer_df.loc[x, 'answer']
                return value
            except:
                try:
                    answer_ids = ast.literal_eval(x)
                    value = ', '.join(answer_df.loc[answer_ids, 'answer'].to_list())
                    return value
                except:
                    return x
        
        df = df.applymap(convert_answer)
        
        df_list.append(df)
    
    manufacturing = df_list[0]
    final_q = manufacturing.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    manufacturing = manufacturing[manufacturing[final_q] != 0]
    
    construction = df_list[1]
    final_q = construction.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    construction = construction[construction[final_q] != 0]
    
    service = df_list[2]
    final_q = service.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    service = service[service[final_q] != 0]
    
    retail = df_list[3]
    final_q = retail.columns[-2]
    region_q = 'Фаолият юритаётган ҳудуд (вилоят):'
    retail = retail[retail[final_q] != 0]
    
    list_dfs = [manufacturing, construction, service, retail]
    
    sheet_names = ['manufacturing', 'construction', 'service', 'retail']
    
    def save_xls(list_dfs, xls_path):
        with ExcelWriter(xls_path) as writer:
            for n, df in enumerate(list_dfs):
                df.to_excel(writer, sheet_names[n], index=False)
            writer.save()
    
    plot_file = BytesIO()
    save_xls(list_dfs, plot_file)
    plot_file.seek(0)
    return plot_file