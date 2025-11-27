# Checklist Final de Smoke Tests e Validação

Este checklist ajuda a validar o fluxo completo do ORKIO v4.5 após o deploy.

## 1. Cadastro e Aprovação de Usuário

- [ ] Crie um novo usuário
- [ ] Aprove o usuário no Admin Console
- [ ] Faça login com o novo usuário

## 2. Criação de Agente

- [ ] Crie um novo agente
- [ ] Verifique se o agente foi criado com sucesso

## 3. Upload de Documento

- [ ] Faça upload de um documento para o agente
- [ ] Verifique se o documento foi associado ao agente

## 4. Resposta do RAG

- [ ] Faça uma pergunta ao agente que exija o conhecimento do documento
- [ ] Verifique se a resposta do RAG está correta

## 5. Download de Anexo

- [ ] Verifique se o anexo do documento está disponível para download

## 6. Isolamento por Tenant

- [ ] Crie um segundo tenant e um segundo usuário
- [ ] Verifique se o segundo usuário não tem acesso aos dados do primeiro

## 7. Usage

- [ ] Verifique se o consumo de tokens está sendo registrado corretamente
