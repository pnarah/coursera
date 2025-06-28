https://hub.docker.com/r/ollama/ollama


docker pull ollama/ollama
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama


pip install ollama

https://github.com/ollama/ollama-python

## Prerequisites
Ollama should be installed and running
Pull a model to use with the library: ollama pull <model> e.g. ollama pull llama3.2
See Ollama.com for more information on the models available.




# Ollama: 
https://ollama.com/
https://github.com/ollama/ollama

Open WebUI:
https://github.com/open-webui/open-webui



https://python.langchain.com/docs/integrations/document_loaders/


# To configure Gemma in Ollama:
https://ai.google.dev/gemma/docs/integrations/ollama

Download and configure the default Gemma 3 variant by opening a terminal window and entering the following command:
```
ollama pull gemma3
```
After completing the download you can confirm the model is available with the following command:
```
ollama list
```

By default, Ollama downloads the 4 billion parameter, 4-bit quantized (Q4_0) Gemma model variant. You can also download and use other sizes of the Gemma model by specifying a parameter size.

Models are specified as <model_name>:<tag>. For the Gemma 3, four sizes: 1B, 4B, 12B and 27B parameters:
```
1B Parameters gemma3:1b
4B Parameters gemma3:4b
12B Parameters gemma3:12b
27B Parameters gemma3:27b
```