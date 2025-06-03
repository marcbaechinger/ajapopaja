import os
import argparse

__all__ = [
    "get_api_key_from_env",
    "get_api_key_from_cmdline_args",
    "get_api_key"
]


def get_api_key_from_env(env_var: str = "GOOGLE_API_KEY"):
    """Retrieves an API key from a specified environment variable.

    Args:
        env_var (str, optional): The name of the environment variable to check.
                                 Defaults to "GOOGLE_API_KEY".

    Returns:
        str or None: The API key string if the environment variable is set,
                     otherwise None.
    """
    try:
        return os.environ[env_var]
    except KeyError:
        return None


def get_api_key_from_cmdline_args():
    """Parses command-line arguments to find an API key.

    It expects an argument like '-a API_KEY' or '--api_key API_KEY'.

    Returns:
        str or None: The API key string if provided via command-line arguments,
                     otherwise None.
    """
    parser = argparse.ArgumentParser(
        'pygen', description='Generate code with Gemini')
    parser.add_argument("-a", "--api_key", help="The Google API key")
    args = parser.parse_args()
    return args.api_key


def get_api_key():
    """Retrieves the API key by first checking command-line arguments,
    then checking the environment variables.

    It first calls `get_api_key_from_cmdline_args()`. If an API key is found,
    it's returned. Otherwise, it calls `get_api_key_from_env()` (with the
    default environment variable "GOOGLE_API_KEY") and returns its result.

    Returns:
        str or None: The API key string if found through either method,
                     otherwise None.
    """
    api_key = get_api_key_from_cmdline_args()
    return api_key if api_key is not None else get_api_key_from_env()


if __name__ == "__main__":
    print(get_api_key())
