import argparse



base_parser = argparse.ArgumentParser(add_help=False)
base_parser.add_argument("--max-subs", '-N', type=int, default=2)
base_parser.add_argument("--password-guess", type=str, default="")
base_parser.set_defaults(command="base")

command_parser = argparse.ArgumentParser(parents=[base_parser], exit_on_error=False)
base_parser.add_argument("extras", type=str, nargs="*", action="extend")

subparsers = command_parser.add_subparsers(title='subcommands',
                                   description='valid subcommands',
                                   help='additional help',
                                   required=True)
# command_parser.add_argument("extras", type=str, nargs="*", action="extend")
default_subparser = subparsers.add_parser("7zip")
default_subparser.set_defaults(command="7zip_direct")
default_subparser.add_argument("extras", type=str, nargs="*", action="extend")
py7zr_parser = subparsers.add_parser("py7zr")
py7zr_parser.set_defaults(command="py7zr")
py7zr_parser.add_argument("extras", type=str, nargs="*", action="extend")
hashcat_parser = subparsers.add_parser("hashcat")
hashcat_parser.set_defaults(command="hashcat")
hashcat_parser.add_argument("extras", type=str, nargs="*", action="extend")




def main():
    try:
        ns = command_parser.parse_args()
        print("Parsed using command_parser")
    except argparse.ArgumentError:
        print("Falling back to base parser")
        ns = base_parser.parse_args()

    print(f"{ns=}")


if __name__ == '__main__':
    main()
