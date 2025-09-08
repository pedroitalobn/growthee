import sqlite3
import os

def update_user_username():
    try:
        # Caminho para o banco de dados
        db_path = "/Users/pedrob/Documents/Dev/enrichStory/prisma/prisma/dev.db"
        
        if not os.path.exists(db_path):
            print(f"❌ Banco de dados não encontrado em: {db_path}")
            return
        
        # Conectar ao banco SQLite
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Verificar se o usuário existe
        cursor.execute("SELECT id, email, full_name FROM users WHERE email = ?", ("client@client.com",))
        user = cursor.fetchone()
        
        if not user:
            print("❌ Usuário client@client.com não encontrado")
            return
        
        user_id, email, full_name = user
        print(f"✅ Usuário encontrado: {email} - {full_name}")
        
        # Atualizar o username
        cursor.execute("UPDATE users SET username = ? WHERE email = ?", ("client", "client@client.com"))
        
        if cursor.rowcount > 0:
            print("✅ Username 'client' atribuído com sucesso ao usuário client@client.com")
        else:
            print("❌ Nenhuma linha foi atualizada")
        
        # Confirmar as mudanças
        conn.commit()
        
        # Verificar a atualização
        cursor.execute("SELECT email, username, full_name FROM users WHERE email = ?", ("client@client.com",))
        updated_user = cursor.fetchone()
        
        if updated_user:
            email, username, full_name = updated_user
            print(f"✅ Verificação: {email} | username: {username} | nome: {full_name}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    update_user_username()