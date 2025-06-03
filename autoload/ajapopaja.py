from ajapopajagit import GitReporter
from api_key import get_api_key
from dataclasses import dataclass
from datetime import datetime
from google import genai
from google.genai import types
from ajapopajabuffer import extract_and_save_fenced_code
import uuid
import os

__all__ = ["AjaPopAja"]

def create_chat(api_key: str, model: str, content_config: types.GenerateContentConfig):
    """Creates a new chat session with the specified API key, model, and content configuration.

    Args:
        api_key: The API key for accessing the generative AI service.
        model: The name of the model to use for the chat.
        content_config: The configuration for content generation.

    Returns:
        A new chat session object.
    """
    client = genai.Client(api_key=api_key)
    return client.chats.create(
        model=model,
        config=content_config
    )

class AjaPopAja:
    def __init__(self, api_key: str, system_instruction: str, workspace_parent:str, log_directory: str) -> None:
        """Initializes an AjaPopAja instance.

        Args:
            api_key: The API key for accessing the generative AI service.
            system_instruction: The system instruction to configure the chat model.
            workspace_parent: The parent directory for creating workspaces.
            log_directory: The directory for storing log files.
        """
        self.uuid = str(uuid.uuid4())
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        path_segment = self.timestamp + "_" + self.uuid
        self.workspace = os.path.join(workspace_parent, path_segment)
        os.makedirs(self.workspace)        
        self.log_directory = os.path.join(log_directory, path_segment)
        self.model_name = "gemini-2.0-flash"
        self.selected_index = 0
        self.prompt_count = 0
        self.prompt_token_count = 0
        self.candidates_token_count = 0
        self.history = History()
        self.git_reporter = GitReporter(self.workspace)
        config= types.GenerateContentConfig(
            system_instruction=system_instruction,
            response_mime_type='text/plain',
        )
        client = genai.Client(api_key=api_key)
        self.chat = client.chats.create(
            model = self.model_name,
            config = config
        )

    def _augment_prompt(self, prompt:str):
        """Augments the user prompt with project context and git information.

        Args:
            prompt: The user's original prompt.

        Returns:
            The augmented prompt string.
        """
        augmented_prompt = f"\n## Project directory tree (`ls -L 5`) ----\n\n"
        augmented_prompt += f"Project root and working directory: {self.workspace} (can't be changed)\n\n" 
        augmented_prompt += self.git_reporter.get_project_tree_info()
        augmented_prompt += "## Git status report ----\n\n"
        commit_hash = self.git_reporter.get_latest_commit_hash()
        if commit_hash is not None:
            augmented_prompt += self.git_reporter.generate_commit_report(commit_hash)
        else:
            augmented_prompt += "Not under version control!\n"
        augmented_prompt += "\n## User prompt ----\n\n" + prompt
        return augmented_prompt

    def prompt(self, prompt:str):
        """Sends a prompt to the chat model and processes the response.

        Args:
            prompt: The user's prompt.

        Returns:
            A tuple containing the selected index and the corresponding HistoryEvent.
        """
        augmented_prompt = self._augment_prompt(prompt)
        response = self.chat.send_message(augmented_prompt)
        print(augmented_prompt)
        self.prompt_count = self.prompt_count + 1
        # Token book keeping.
        prompt_tokens = 0
        candidates_tokens = 0
        if response.usage_metadata is not None:
            metadata = response.usage_metadata
            prompt_tokens: int = metadata.prompt_token_count if metadata.prompt_token_count is not None else 0
            candidates_tokens: int = metadata.candidates_token_count if metadata.candidates_token_count is not None else 0
        self.prompt_token_count = self.prompt_token_count + prompt_tokens
        self.candidates_token_count = self.candidates_token_count + candidates_tokens

        # Fallback if Code ouput failed. Should not happen.
        responseText = ""
        for part in response.candidates[0].content.parts:
            if part.text is not None:
                responseText += part.text
        self.history.add(prompt, responseText, prompt_tokens, candidates_tokens)
        self.history.truncate(20)
        self.selected_index = len(self.history.entries) - 1
        self.dump_report(
            prompt, 
            responseText, 
            prompt_tokens,
            candidates_tokens,
            self.prompt_count,
            self.log_directory)
        return self.get_selected()

    def dump_report(
        self,
        prompt: str,
        response: str,
        input_tokens: int,
        output_tokens: int,
        prompt_sequence: int,
        directory: str
    ):
        """Dumps a report of the interaction to a markdown file.

        Args:
            prompt: The prompt sent to the model.
            response: The response received from the model.
            input_tokens: The number of tokens in the input.
            output_tokens: The number of tokens in the output.
            prompt_sequence: The sequence number of the prompt.
            directory: The directory to save the report in.
        """
        now = datetime.now()
        date_time_string = now.strftime("%Y-%m-%d %H:%M:%S")

        report_header = f"""\n## Turn Report\n
**When:** {date_time_string}\n**Prompt Sequence:** {prompt_sequence}\n
### Prompt\n{prompt}

### Token Information\n*   Input Tokens: {input_tokens}\n*   Output Tokens: {output_tokens}\n\n---\n"""

        markdown_content = report_header + response

        # write the file
        file_name = f"turn-{prompt_sequence}.md"
        file_path = os.path.join(directory, file_name)
        os.makedirs(directory, exist_ok=True)
        with open(file_path, "w") as f:
            f.write(markdown_content)


    def get_total_token_count(self):
        """Gets the total number of tokens used in the chat session.

        Returns:
            The total token count.
        """
        return self.prompt_token_count + self.candidates_token_count

    def get_prompt_token_count(self):
        """Gets the total number of prompt tokens used in the chat session.

        Returns:
            The prompt token count.
        """
        return self.prompt_token_count

    def get_candidates_token_count(self):
        """Gets the total number of candidates tokens used in the chat session.

        Returns:
            The candidates token count.
        """
        return self.candidates_token_count

    def get_selected_response(self):
        """Gets the response content of the currently selected history entry.

        Returns:
            The response string, or None if no entry is selected.
        """
        _, event = self.get_selected()
        if event is not None:
            return event.response

    def get_selected_prompt(self):
        """Gets the prompt content of the currently selected history entry.

        Returns:
            The prompt string, or None if no entry is selected.
        """
        _, event = self.get_selected()
        if event is not None:
            return event.prompt
        return None

    def get_last_response(self):
        """Gets the response content of the last history entry.

        Returns:
            The response string, or None if history is empty.
        """
        event = self.history.get_last_entry()
        if event is not None:
            return event.response
        return None

    def get_last_prompt(self):
        """Gets the prompt content of the last history entry.

        Returns:
            The prompt string, or None if history is empty.
        """
        event = self.history.get_last_entry()
        if event is not None:
            return event.prompt
        return None

    def select_previous(self):
        """Selects the previous entry in the history.

        Returns:
            A tuple containing the new selected index and the corresponding HistoryEvent,
            or None if already at the beginning of the history.
        """
        if self.selected_index > 0:
            self.selected_index = self.selected_index - 1
            return self.get_selected()
        return None

    def select_next(self):
        """Selects the next entry in the history.

        Returns:
            A tuple containing the new selected index and the corresponding HistoryEvent,
            or None if already at the end of the history.
        """
        num_entries = len(self.history.entries)
        if self.selected_index < num_entries - 1:
            self.selected_index = self.selected_index + 1
            return self.get_selected()
        return None

    def get_last(self):
        """Gets the last entry in the history.

        Returns:
            A tuple containing the index of the last entry and the HistoryEvent itself,
            or (-1, None) if the history is empty.
        """
        if len(self.history.entries) == 0:
            return -1, None
        return len(self.history.entries) - 1, self.history.get_last_entry()

    def get_selected(self):
        """Gets the currently selected entry in the history.

        Returns:
            A tuple containing the selected index and the HistoryEvent,
            or (-1, None) if the history is empty.
        """
        if len(self.history.entries) == 0:
            return -1, None
        return self.selected_index, self.history.entries[self.selected_index]

    def execute_selected_code_section(self):
        """Extracts and executes the code section from the selected history entry's response.

        The code is saved to a temporary file ".exec.sh" in the workspace and then executed.
        """
        extract_and_save_fenced_code(self.workspace, ".exec.sh")
        self.git_reporter.execute_bash_script(".exec.sh")


@dataclass(frozen=True)
class HistoryEvent:
    """Represents a single event in the chat history.

    Attributes:
        prompt: The prompt sent to the model.
        response: The response received from the model.
        prompt_token_count: The number of tokens in the prompt.
        candidates_token_count: The number of tokens in the response.
        timestamp: The timestamp of when the event was created.
    """
    prompt: str
    response: str
    prompt_token_count: int
    candidates_token_count: int
    timestamp: float = datetime.now().timestamp()

class History:
    def __init__(self) -> None:
        """Initializes a new History instance."""
        self.entries: list[HistoryEvent] = []

    def add(self, prompt: str, response: str, prompt_token_count: int, candidates_token_count: int):
        """Adds a new event to the history.

        Args:
            prompt: The prompt sent to the model.
            response: The response received from the model.
            prompt_token_count: The number of tokens in the prompt.
            candidates_token_count: The number of tokens in the response.
        """
        self.entries.append(HistoryEvent(prompt, response, prompt_token_count, candidates_token_count))

    def get_last_entry(self):
        """Gets the last entry in the history.

        Returns:
            The last HistoryEvent, or None if the history is empty.
        """
        history_len = len(self.entries)
        return None if history_len == 0 else self.entries[history_len - 1]

    def truncate(self, max_length):
        """Truncates the history to a maximum length.

        If the number of entries exceeds max_length, the oldest entries are removed.

        Args:
            max_length: The maximum number of entries to keep in the history.
        """
        if len(self.entries) > max_length:
            start_index = len(self.entries) - max_length
            self.entries = self.entries[start_index:]


if __name__ == "__main__":
    api_key = get_api_key()
    if api_key is None:
        print("please provide and api key")
        exit()

    system_instruction = (
        "You are an expert vim tutor."
        "You give clear an concise advise on how to use vim."
        "Your output are vim commands or vimscript function that help the user to edit text with vim."
        "Start with the sequence of commands or the functions and then explain step by step how the user can achieve the declared goal."
        "Format you output in markdown format."
    )

    def print_history_entry(entry):
        print("prompt" + (10 * "-"))
        print(entry.prompt)
        print("response" + (10 * "-"))
        print(entry.response)
        print("tokens" + (10 * "-"))
        print(f"prompt tokens: {entry.prompt_token_count}, candidates tokens: {entry.candidates_token_count}" )
        print(f"total prompts: {agent.prompt_token_count}, total candidates: {agent.candidates_token_count}" )


    agent = AjaPopAja(api_key, system_instruction, '/tmp')
    prompt = ""
    while prompt is not None:
        prompt = input("# ")
        if prompt == "q":
            prompt = None
            continue
        if prompt == "n":
            entry = agent.select_next()
            if entry is not None:
                print_history_entry(entry)
            continue
        if prompt == "p":
            entry = agent.select_previous()
            if entry is not None:
                print_history_entry(entry)
            continue
        elif prompt != "l":
            agent.prompt(prompt)
        last = agent.history.get_last_entry()
        if last is not None:
            print_history_entry(last)


