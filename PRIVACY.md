# Privacy policy

AI Team Room is a local-first application. By default, it binds only to the
loopback interface (`127.0.0.1`) and stores meeting data in a local SQLite
database on the user's computer.

The application does not transmit meeting content, tokens, usage data,
telemetry, or personal information to Madoro Studio, SignPath, or any other
networked system. Network communication occurs only when the user explicitly
requests or configures it, including:

- connecting a participant to the local room;
- enabling the expert `--allow-network` option for LAN access; or
- directing an AI tool or other client to access an external service.

AI Team Room does not control the privacy behavior of third-party AI tools,
model providers, operating systems, or services that a user chooses to connect.
Their own privacy policies apply to those products.

Meeting records remain under the user's control and can be removed by deleting
the local AI Team Room data directory. The participant CLI also stores only its
latest numeric delivery cursor in a local file named with a one-way hash of the
room URL and participant token; it does not store the token itself. See
[SECURITY.md](SECURITY.md) for the security model and known limitations.

Questions about this policy may be submitted through the repository's GitHub
issue tracker. Do not include private meeting content, access tokens, or other
sensitive information in a public issue.
