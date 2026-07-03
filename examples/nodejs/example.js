const { Configuration, OpenAIApi } = require("openai");
const configuration = new Configuration({
    basePath: "http://localhost:8000/v1",
    apiKey: "sk-your-llm-key",
});
const openai = new OpenAIApi(configuration);
(async () => {
    const completion = await openai.createChatCompletion({
        model: "gpt-4",
        messages: [
            {role: "system", content: "You are helpful."},
            {role: "user", content: "Latest news <context>old article</context>"}
        ],
    });
    console.log(completion.data.choices[0].message.content);
})();