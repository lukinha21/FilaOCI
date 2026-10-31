# Filas OCI (Queue) em Python + Flask

Reimplementação, em **Python (Flask)**, do exemplo `appdemo3fila` (originalmente Node.js + Express + EJS)
do serviço de **Filas (Queue)** da Oracle Cloud Infrastructure.

O app web tem um **produtor** (publica mensagens na fila) e um **consumidor** (lê as mensagens, mostra na
tela e as remove da fila), com e sem **canais**. Toda a comunicação usa a API REST da OCI, com as
requisições assinadas com a chave privada do usuário.

> O envio de e-mail do exemplo original foi mantido como recurso **opcional** e vem **desligado**.
> Para usar o projeto não é preciso configurar e-mail nem SMTP (veja a seção "E-mail (opcional)").

## Estrutura

| Arquivo | Responsabilidade | Equivalente no original |
|---|---|---|
| `app.py` | Rotas web (`/`, `/publicar`, `/publicarCanal`, `/consumir`, `/consumirCanal`) | `app.js` (Express) |
| `services.py` | Regra de negócio: publicar e consumir (apagar ou devolver à fila) | lógica dentro das rotas |
| `queue_client.py` | Endpoints da fila: PutMessages, GetMessages, DeleteMessage, UpdateMessage | URLs montadas no `app.js` |
| `oci_http_request.py` | Assinatura da requisição (Request Signatures) e envio HTTP | `ociHttpRequest.js` |
| `config.py` | Configuração via variáveis de ambiente / `.env` | valores fixos no código |
| `templates/index.html` | Interface (Produtor, Consumidor e passo a passo) | `views/index.ejs` |
| `email_sender.py` | Envio por SMTP (opcional, desligado por padrão) | `enviarEmail` (nodemailer) |

## Como executar

1. Instale o **Python 3.12** (marque "Add python.exe to PATH").
2. Instale as dependências: `py -3.12 -m pip install -r requirements.txt`
3. Na OCI, gere uma chave de API (My profile > API keys > Add API key) e coloque o `config` e o `.pem`
   na pasta `.oci` do projeto. O `key_file` do `config` deve apontar para o `.pem`.
4. Crie o arquivo `.env` na pasta do projeto:

   ```
   OCI_CONFIG_FILE=C:/caminho/do/projeto/.oci/config
   OCI_QUEUE_ID=ocid1.queue.oc1.phx.xxxxxxxx
   OCI_QUEUE_ENDPOINT=https://cell-1.queue.messaging.us-phoenix-1.oci.oraclecloud.com
   OCI_QUEUE_CHANNEL=canal1
   ```

   O OCID e o endpoint estão na página de detalhes da fila (Serviços ao Desenvolvedor > Filas).
5. Execute: `py -3.12 app.py` e abra http://localhost:3000

## Como usar

- **PUBLICAR / PUBLICAR - CANAL:** envia a mensagem (JSON `{"email", "msg"}`) para a fila na OCI.
  O campo "E-mail" é apenas um dado do payload: nada é enviado para esse endereço.
- **CONSUMIR / CONSUMIR - CANAL:** retira mensagens da fila, **mostra na tela** e as remove da OCI
  (DeleteMessage). Também aceita mensagens de texto simples criadas pelo botão "Enviar mensagem"
  do console da OCI.
- Se o processamento de uma mensagem falhar, ela volta para a fila (UpdateMessage) e, após o máximo
  de tentativas de entrega, vai para a DLQ.
- Atenção: com retenção de 1 minuto na fila, mensagens não consumidas nesse tempo são excluídas pela OCI.

## E-mail (opcional)

O exemplo original disparava um e-mail ao consumir cada mensagem. Esse comportamento continua disponível:
defina `ENVIAR_EMAIL=true` e as variáveis `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER` e `SMTP_PASSWORD` no `.env`
(no Gmail, use uma "senha de app"). Com ele ligado, se o envio falhar a mensagem não é apagada: volta para a fila.

## Melhorias em relação ao exemplo original

- **Bug corrigido (envio não aguardado):** no original, o envio era por callback e não era aguardado;
  uma falha nunca caía no `catch` e a mensagem era apagada mesmo sem ter sido processada.
  Agora a mensagem só é apagada após o sucesso.
- **Bug corrigido (payload):** o JS lia `msgFila.email`, mas o dado está no `content` (JSON).
  Agora o payload é interpretado e validado.
- **Bug corrigido (`/consumirCanal`):** o DELETE usava a variável `alteracao` antes de ela existir
  (ReferenceError), então a mensagem **nunca era apagada** e sempre caía no `catch`.
- **Bug corrigido:** `response.json()` quebrava em respostas sem corpo (DELETE/PUT).
- **Sem duplicação:** `publicar`/`publicarCanal` e `consumir`/`consumirCanal` usam a mesma função,
  com o canal como parâmetro; o mesmo vale para o JavaScript da página.
- **Exibição segura:** as mensagens aparecem na tela via `textContent`, sem executar HTML vindo da fila.
- **Resposta útil:** o consumo informa quantas mensagens foram recebidas, removidas e devolvidas
  (o original respondia "Retirado da fila." antes de terminar o processamento).
- **Segurança:** credenciais e OCID fora do código; receipt codificado na URL; erros da OCI tratados.
- **Organização:** camadas separadas (rotas, serviços, cliente da fila, HTTP), type hints, dataclasses,
  logging e comentários explicando as decisões; `criar_app()` permite testar sem a OCI.

## Segurança

Não envie nem publique a pasta `.oci`, os arquivos `.pem` e o `.env` (use `.gitignore`).
Quem tiver a chave privada consegue acessar a conta da OCI.

## DOCUMENTAÇÃO
LINK: https://pdfhost.io/v/VdcbeKhXmz_FilaOCI
