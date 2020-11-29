# Baseado no código do blog:
# https://blog.nilo.pro.br/posts/2014-08-30-servidor-de-chat-com-websockets-e-asyncio/

import asyncio
import websockets
import shlex

class Servidor:
    def __init__(self):
        self.conectados = []
    
    @property
    def nconectados(self):
        return len(self.conectados)
    
    async def conecta(self, websocket, path):
        cliente = Cliente(self, websocket, path)
        if cliente not in self.conectados:
            self.conectados.append(cliente)
            print("Novo cliente conectado. Total: {0}".format(self.nconectados))            
        await cliente.gerencia()

    async def envia_a_todos(self, origem, mensagem):
        print("Enviando a todos")
        for cliente in self.conectados:            
            if origem != cliente and cliente.conectado:
                print("Enviando de <{0}> para <{1}>: {2}".format(origem.nome, cliente.nome, mensagem))
                await cliente.envia("{0} >> {1}".format(origem.nome, mensagem))

    async def altera_cliente(self, origem, novo_nome):
        print("<{0}> alterou nome para <{1}>".format(origem.nome, novo_nome))
        for cliente in self.conectados:            
            if origem != cliente and cliente.conectado:
                print("Avisando <{0}> que <{1}> alterou nome".format(cliente.nome, origem.nome))
                await cliente.envia("{0} alterou nome para {1}".format(origem.nome, novo_nome))

    async def novo_cliente(self, origem):
        print("<{0}> entrou no chat".format(origem.nome))
        for cliente in self.conectados:            
            if origem != cliente and cliente.conectado:
                print("Avisando <{0}> que <{1}> entrou no chat".format(cliente.nome, origem.nome))
                await cliente.envia("{0} entrou no chat".format(origem.nome))


    async def envia_a_destinatario(self, origem, mensagem, destinatario):        
        for cliente in self.conectados:            
            if cliente.nome == destinatario and origem != cliente and cliente.conectado:
                print("Enviando de <{0}> para <{1}>: {2}".format(origem.nome, cliente.nome, mensagem))
                await cliente.envia("PRIVADO de {0} >> {1}".format(origem.nome, mensagem))
                return True
        return False

    def verifica_nome(self, nome):
        for cliente in self.conectados:
            if cliente.nome and cliente.nome == nome:
                return False
        return True


class Cliente:    
    def __init__(self, servidor, websocket, path):
        self.cliente = websocket
        self.servidor = servidor
        self.nome = None        
    
    @property
    def conectado(self):
        return self.cliente.open

    async def gerencia(self):
        try:
            await self.envia("Bem vindo ao servidor.")
            while True:
                mensagem = await self.recebe()
                if mensagem:
                    print("{0} < {1}".format(self.nome, mensagem))
                    await self.processa_comandos(mensagem)                                            
                else:
                    break
        except Exception:
            print("Erro")
            raise        
        finally:
            self.servidor.desconecta(self)

    async def envia(self, mensagem):
        await self.cliente.send(mensagem)

    async def recebe(self):
        mensagem = await self.cliente.recv()
        return mensagem

    async def processa_comandos(self, mensagem):        
        if mensagem.strip().startswith("/"):
            comandos=shlex.split(mensagem.strip()[1:])
            if len(comandos)==0:
                await self.envia("Comando inválido")
                return
            print(comandos)
            comando = comandos[0].lower()            
            if comando == "nome":
                await self.altera_nome(comandos)
            elif comando == "apenas":
                await self.apenas_para(comandos)
            else:
                await self.envia("Comando desconhecido")
        else:
            if self.nome:
                await self.servidor.envia_a_todos(self, mensagem)
            else:
                await self.envia("Identifique-se para enviar mensagens. (Mudar nome: /nome [nome])")

    async def altera_nome(self, comandos):                
        if len(comandos)>1 and self.servidor.verifica_nome(comandos[1]):
            if not self.nome:
                self.nome = comandos[1]
                await self.servidor.novo_cliente(self)
            else:
                await self.servidor.altera_cliente(self,comandos[1])
                self.nome = comandos[1]
            await self.envia("Nome alterado com sucesso para {0}".format(self.nome))
        else:
            await self.envia("Nome em uso ou inválido. Escolha um outro.")

    async def apenas_para(self, comandos):
        if len(comandos)<3:
            await self.envia("Comando incorreto. /apenas Destinatário mensagem")
            return
        destinatario = comandos[1]
        mensagem = " ".join(comandos[2:])
        enviado = await self.servidor.envia_a_destinatario(self, mensagem, destinatario)
        if not enviado:
            await self.envia("Destinatário {0} não encontrado. Mensagem não enviada.".format(destinatario))



servidor=Servidor()
loop=asyncio.get_event_loop()

start_server = websockets.serve(servidor.conecta, 'localhost', 50007)

try:
    loop.run_until_complete(start_server)
    loop.run_forever()
finally:
    start_server.close()