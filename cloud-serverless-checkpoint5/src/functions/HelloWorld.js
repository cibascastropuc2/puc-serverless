const { app } = require('@azure/functions');

app.http('HelloWorld', {
    methods: ['GET'],
    authLevel: 'anonymous',
    handler: async (request, context) => {

        return {
            status: 200,
            body: 'Olá! Minha primeira função serverless está funcionando!'
        };
    }
});