from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

# Create a couple of Global Variables
TEMPERATURE = 0.2
MAX_TOKENS = 512

# Code generation llm with gpt-3.5
openai_gpt35 = ChatOpenAI(temperature=TEMPERATURE, 
                 model="gpt-3.5-turbo",
                 verbose=False,
                 max_tokens=300,
                 )

openai_gpt4o_mini = ChatOpenAI(temperature=TEMPERATURE, 
                 model="gpt-4o-mini",
                 verbose=False,
                 max_tokens=300,
                 )

openai_4o_mini_json = ChatOpenAI(temperature=TEMPERATURE,
        model="gpt-4o-mini",
        max_tokens=300,
        model_kwargs={ "response_format": { "type": "json_object" } }
        )

# Router llm: Choose OpenAI-GPT4 for better reasoning 
openai_gpt4 = ChatOpenAI(temperature=0.1, 
                 model="gpt-4-0125-preview",
                 verbose=False,
                 max_tokens=50,
                 )


openai_gpt4o = ChatOpenAI(temperature=0.1, 
        model='gpt-4o',
        # max_tokens=self.max_tokens,,
        )

# define the Anthropic chat client
# overall style seems consistent with the OpenAI chat client
claude_sonnet = ChatAnthropic(
        model='claude-3-5-sonnet-20241022',
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
        )

claude_opus = ChatAnthropic(
        model='claude-3-opus-20240229',
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
        )

claude_haiku = ChatAnthropic(
        model='claude-3-5-haiku-20241022',
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS
        )
