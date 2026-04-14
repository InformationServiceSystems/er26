"""Generate low-formal management decision tasks from real software incident postmortems."""
import pandas as pd
from pathlib import Path
import json
import sys
import re
import argparse

sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.local_model import LocalChatModel

OUT_PATH = Path("data/low_formal/low_formal_tasks_draft.csv")

MODEL_DIR = "meta-llama/Llama-3.1-8B-Instruct"
LOAD_IN_4BIT = False  # FP16 on Apple Silicon

# Curated incident seeds: real postmortems with enough narrative detail.
# Each seed provides a grounded scenario the model expands into a decision task.
INCIDENT_SEEDS = [
    {
        "category": "architecture",
        "company": "GitHub",
        "incident": "A 43-second network partition between the US East Coast primary datacenter and the US West Coast replica caused MySQL orchestrator to promote a West Coast replica to primary. When connectivity restored, both sites believed they were primary. The split-brain resulted in data divergence: 24 hours of out-of-date data on some tables. Automated failback was impossible because writes had occurred on both sides. GitHub degraded service for over 24 hours while engineers manually reconciled data. The incident revealed that their replication topology lacked proper fencing and split-brain prevention.",
        "source": "https://blog.github.com/2018-10-30-oct21-post-incident-analysis/"
    },
    {
        "category": "architecture",
        "company": "Atlassian",
        "incident": "During routine maintenance, a script intended to disable a small set of Atlassian cloud instances accidentally deleted 775 customer sites including their Jira, Confluence, and OpsGenie data. The deletion script used incorrect parameters, passing site IDs instead of legacy app IDs. Restoration required rebuilding each site individually from backups, a process that took up to 14 days for some customers. The incident exposed that Atlassian lacked a bulk restore capability and had no 'soft delete' safeguard for site-level operations.",
        "source": "https://www.atlassian.com/engineering/post-incident-review-april-2022-outage"
    },
    {
        "category": "deployment",
        "company": "Knight Capital",
        "incident": "Knight Capital deployed new trading software to production but failed to update the code on one of eight servers. The old code on that server reactivated a dormant function that had been repurposed as a test flag. This function executed trades at unfavorable prices instead of routing them normally. In 45 minutes, the system executed 4 million trades across 154 stocks, accumulating a $460 million loss. The company had no kill switch, no automated position limits, and no deployment verification that checked all servers matched. Knight Capital was rescued by a $400M emergency investment but lost its independence.",
        "source": "https://dougseven.com/2014/04/17/knightmare-a-devops-cautionary-tale/"
    },
    {
        "category": "deployment",
        "company": "CrowdStrike",
        "incident": "A content configuration update to CrowdStrike's Falcon sensor caused a Windows kernel-level crash (BSOD) on 8.5 million machines worldwide. The update contained undetected errors in sensor content data that triggered a logic error in the content interpreter. Because the sensor runs at kernel level, the crash was unrecoverable without manual intervention — each affected machine required physical or remote access to boot into Safe Mode and delete the problematic file. Airlines, hospitals, banks, and government agencies were affected. The update had bypassed the staged rollout process that CrowdStrike's own policies required.",
        "source": "https://www.crowdstrike.com/falcon-content-update-remediation-and-guidance-hub/"
    },
    {
        "category": "scaling",
        "company": "Epic Games",
        "incident": "Fortnite reached a new peak of 3.4 million concurrent users, overwhelming multiple backend services simultaneously. The matchmaking service hit connection pool limits, the profile service exceeded its database write throughput, and the party service ran out of memory. Each service failure cascaded: players couldn't form parties, which caused retry storms that further overloaded matchmaking. The team had load-tested to 2 million CCU but assumed linear scaling beyond that. Recovery required manually scaling each service independently while managing thundering herd effects from millions of reconnecting clients.",
        "source": "https://web.archive.org/web/20220430011642/https://www.epicgames.com/fortnite/en-US/news/postmortem-of-service-outage-at-3-4m-ccu"
    },
    {
        "category": "scaling",
        "company": "Honeycomb",
        "incident": "Honeycomb experienced multiple cascading incidents over several weeks as rapid customer growth exceeded their query engine's capacity. The query system used a shared resource pool where expensive queries from large customers starved smaller customers' queries. When the team added capacity, the new nodes took too long to warm their caches, causing further performance degradation during scaling events. Their alerting was based on global averages, masking per-customer degradation until individual customers escalated. The team had to redesign their query isolation model, implement per-customer resource limits, and build customer-specific SLO monitoring.",
        "source": "https://www.honeycomb.io/blog/incident-review-designed-failing/"
    },
    {
        "category": "data_loss",
        "company": "GitLab",
        "incident": "A GitLab database administrator, working late to resolve a replication lag issue, accidentally ran rm -rf on the production PostgreSQL data directory instead of the replica directory. The team discovered that five out of six backup methods had failed silently: LVM snapshots were not being taken, pg_dump hadn't run in months due to a configuration error, Azure disk snapshots were not enabled, S3 backups had never been tested, and the replication setup itself was broken. Only a six-hour-old LVM snapshot from an ad-hoc manual backup saved the company. GitLab lost approximately six hours of production data including issues, merge requests, and CI/CD pipelines.",
        "source": "https://about.gitlab.com/blog/2017/02/10/postmortem-of-database-outage-of-january-31/"
    },
    {
        "category": "data_loss",
        "company": "Razorpay",
        "incident": "Razorpay's primary MySQL database experienced a hardware failure that triggered an RDS Multi-AZ failover. However, the failover revealed that binary logging (binlog) had been misconfigured: the standby replica was hours behind the primary. When the primary failed and the standby was promoted, all transactions written to the primary but not yet replicated were lost. The team discovered that their monitoring only checked replication status, not replication lag. The configuration error had existed for months but was never detected because they had never tested a failover end-to-end.",
        "source": "https://web.archive.org/web/20250207075402/https://razorpay.com/blog/day-of-rds-multi-az-failover/"
    },
    {
        "category": "security",
        "company": "CircleCI",
        "incident": "An attacker compromised a CircleCI engineer's laptop with malware that stole a valid SSO session token backed by 2FA. Using this token, the attacker accessed CircleCI's internal systems including production databases and customer environment variables containing secrets (API keys, tokens, passwords). The attacker exfiltrated data over two weeks before detection. CircleCI had to advise all customers to rotate every secret stored in CircleCI. The incident revealed that session tokens had no expiration tied to device health checks, and there was no anomaly detection for unusual data access patterns from authenticated sessions.",
        "source": "https://circleci.com/blog/jan-4-2023-incident-report/"
    },
    {
        "category": "security",
        "company": "Heroku/Salesforce",
        "incident": "Attackers exfiltrated OAuth tokens from Heroku's internal systems, gaining access to private GitHub repositories of Heroku customers including npm. The compromised tokens allowed reading source code and potentially injecting code. Heroku's initial investigation was slow; they revoked all OAuth tokens only after GitHub detected the breach independently. The incident revealed that Heroku stored machine-to-machine OAuth tokens in a database without additional encryption, and their audit logging for token usage was insufficient to detect the breach quickly.",
        "source": "https://blog.heroku.com/april-2022-incident-review"
    },
    {
        "category": "config_error",
        "company": "Facebook/Meta",
        "incident": "A routine BGP configuration change to Facebook's backbone routers contained an error that withdrew all BGP route announcements for Facebook's DNS servers. Because Facebook's internal tools (including the remote access systems engineers would use to fix the problem) all depended on the same DNS infrastructure, engineers were locked out of the systems needed to reverse the change. Physical access to the datacenter was required, but the badge access system also depended on Facebook's network. The total outage lasted approximately six hours, affecting Facebook, Instagram, WhatsApp, and Oculus for 3.5 billion users.",
        "source": "https://engineering.fb.com/2021/10/05/networking-traffic/outage-details/"
    },
    {
        "category": "config_error",
        "company": "Cloudflare",
        "incident": "A regular expression update to Cloudflare's Web Application Firewall (WAF) consumed excessive CPU on every edge server globally. The regex contained catastrophic backtracking: on certain inputs, evaluation time grew exponentially. Because the WAF runs inline on every HTTP request, CPU exhaustion caused all Cloudflare proxy services to return 502 errors worldwide. The update had been deployed globally without staged rollout or canary testing. The team had to disable the entire WAF to restore service, then redeploy without the problematic rule. Total downtime was 27 minutes but affected millions of websites.",
        "source": "https://web.archive.org/web/20211006055154/https://blog.cloudflare.com/details-of-the-cloudflare-outage-on-july-2-2019/"
    },
    {
        "category": "config_error",
        "company": "Amazon/AWS",
        "incident": "An engineer executing a command to remove a small number of S3 subsystem servers mistyped the command, causing a much larger set of servers to be removed than intended. This took down both the S3 index subsystem (which manages metadata for all objects) and the S3 placement subsystem (which manages storage allocation). Because so many AWS services depend on S3, the failure cascaded across the US-EAST-1 region: EC2 couldn't launch instances, Lambda couldn't execute functions, and even the AWS Service Health Dashboard couldn't update because it was hosted on S3. Full recovery took over four hours.",
        "source": "https://aws.amazon.com/message/41926/"
    },
    {
        "category": "migration",
        "company": "Healthcare.gov",
        "incident": "The US government's Affordable Care Act healthcare marketplace website launched on October 1, 2013, and immediately failed under load. The project involved 55 contractors managed by CMS with no single technical integrator. The system had never been load-tested end-to-end before launch. The identity verification service couldn't handle concurrent requests. The enrollment system had a design flaw requiring users to create accounts before browsing plans, creating a bottleneck at registration. The database supporting eligibility determinations had significant performance issues. Only 6 people successfully enrolled on launch day despite millions of visitors.",
        "source": "https://web.archive.org/web/20201108122248/https://www.bloomberg.com/opinion/articles/2015-09-16/how-healthcare-gov-went-so-so-wrong"
    },
    {
        "category": "migration",
        "company": "Basecamp",
        "incident": "Basecamp's primary MySQL database hit the maximum value for a signed 32-bit integer primary key on a high-volume table. When the auto-increment counter overflowed, all new INSERT operations failed, putting the application into a read-only state. The team had known about the approaching limit but had estimated they had months remaining based on average growth rates. A traffic spike accelerated the timeline. The fix required an ALTER TABLE to change the column to BIGINT, but on a table with hundreds of millions of rows, this operation took hours during which the service remained degraded.",
        "source": "https://web.archive.org/web/20220529044310/https://m.signalvnoise.com/postmortem-on-the-read-only-outage-of-basecamp-on-november-9th-2018/"
    },
    {
        "category": "migration",
        "company": "Instapaper",
        "incident": "Instapaper's hosted MySQL database on RDS hit the 2 TB storage limit for their instance type. When the database reached the limit, it became read-only — users couldn't save new articles or update their accounts. The team discovered they couldn't simply resize the instance because their RDS configuration didn't support online storage expansion. Migrating to a larger instance required creating a new database, copying 2 TB of data, and switching DNS — a process that took over 31 hours. During this time, the service was partially functional but users couldn't save new content.",
        "source": "https://web.archive.org/web/20211124170124/https://medium.com/making-instapaper/instapaper-outage-cause-recovery-3c32a7e9cc5f"
    },
    {
        "category": "process",
        "company": "Fastly",
        "incident": "A single customer configuration change triggered an undiscovered software bug in Fastly's global CDN, causing 85% of Fastly's network to return errors. Major websites including Amazon, Reddit, The New York Times, and the UK government's gov.uk went offline. The bug had existed in the software for weeks but required a specific, rare configuration pattern to trigger. Fastly's canary deployment process for customer configs existed but didn't cover this code path. The fix was deployed within 49 minutes, but the incident raised questions about CDN concentration risk and the fragility of internet infrastructure dependencies.",
        "source": "https://www.fastly.com/blog/summary-of-june-8-outage"
    },
    {
        "category": "process",
        "company": "Dropbox",
        "incident": "During a planned OS upgrade across Dropbox's server fleet, the upgrade automation inadvertently wiped the local storage on machines in the metadata tier. The upgrade process was designed to reformat and reinstall the OS, which was correct for stateless application servers but catastrophic for servers storing database files. The deployment system didn't distinguish between server roles, and there was no pre-upgrade check to verify whether a machine held persistent data. The team had to restore from backups, but the restoration process surfaced additional issues: some backup verification jobs had been silently failing.",
        "source": "https://blogs.dropbox.com/tech/2014/01/outage-post-mortem/"
    },
    {
        "category": "crisis",
        "company": "Sentry",
        "incident": "Sentry discovered that incorrect Amazon S3 bucket permissions had been exposing customer error-tracking data to the public internet. The misconfiguration had existed since the S3 bucket was created — default permissions were overly permissive and the team hadn't applied a restrictive bucket policy. The exposure was discovered by a security researcher, not by Sentry's own monitoring. Sentry had no S3 bucket auditing in place and no automated checks for public accessibility of storage resources. The incident required notifying all affected customers, conducting a forensic analysis of access logs to determine if data had been accessed, and implementing organization-wide storage security policies.",
        "source": "https://blog.sentry.io/2016/06/14/security-incident-june-12-2016"
    },
    {
        "category": "crisis",
        "company": "NPM/GitHub",
        "incident": "An attacker compromised an npm maintainer's account and published malicious versions of eslint-scope and eslint-config-eslint packages. The malicious code attempted to steal npm tokens from developers' machines during package installation, sending them to the attacker's server. The compromised packages were downloaded thousands of times before detection. npm had no automated analysis of published package contents, no anomaly detection for unusual publish patterns (the maintainer hadn't published in months), and no two-factor authentication requirement for package publishing. The incident accelerated npm's adoption of 2FA and automated malware scanning.",
        "source": "https://eslint.org/blog/2018/07/postmortem-for-malicious-package-publishes"
    },
    {
        "category": "architecture",
        "company": "Discord",
        "incident": "A Redis cluster used for Discord's session state management experienced a primary node failure. The automatic failover promoted a replica, but the replica was behind the primary due to replication lag. When the new primary came online, it had stale session data, causing millions of users to experience inconsistent state. The reconnection storm from affected clients overwhelmed the new primary before its cache could warm. Recovery required a full cluster restart with manual data reconciliation. The incident revealed that Discord's Redis cluster had grown beyond the capacity that their replication topology could safely handle.",
        "source": "https://status.discordapp.com/incidents/qk9cdgnqnhcn"
    },
    {
        "category": "architecture",
        "company": "Buildkite",
        "incident": "Buildkite's database was running on an oversized instance. To reduce costs, the team migrated to a smaller instance during a maintenance window. However, the new instance couldn't handle peak load the following Monday morning. Build queues backed up, API response times increased exponentially, and the connection pool was exhausted within minutes. The cascading failure took down the dashboard, webhook processing, and the API. The team couldn't immediately scale back up because the migration had already released the old instance. Provisioning a new larger instance and restoring from backup took several hours.",
        "source": "https://building.buildkite.com/outage-post-mortem-for-august-23rd-82b619a3679b"
    },
    {
        "category": "deployment",
        "company": "TravisCI",
        "incident": "An automated cleanup job designed to remove old Google Compute Engine VM images used an age-based filter that was too aggressive. It deleted the stable base images that all new CI builds depended on. When developers triggered builds, TravisCI couldn't provision build environments because the base images no longer existed. The cleanup job had been added recently without proper guardrails: no minimum retention count, no confirmation for images tagged as 'stable,' and no alert when deletion volume exceeded normal thresholds. Recovery required rebuilding all base images from scratch, a process that took most of a day.",
        "source": "https://web.archive.org/web/20221220114914/https://blog.travis-ci.com/2016-09-30-the-day-we-deleted-our-vm-images/"
    },
    {
        "category": "scaling",
        "company": "Foursquare",
        "incident": "Foursquare experienced two extended outages totaling 17 hours when their MongoDB deployment couldn't handle the load. The primary issue was that one of their shards had grown disproportionately large — data distribution across shards was uneven because the shard key choice (user ID) created hotspots. When that shard's working set exceeded available RAM, MongoDB fell off a performance cliff as it began reading from disk. Adding more RAM temporarily helped but the fundamental problem was the data model. Foursquare had to re-architect their sharding strategy and rebalance data across shards, a multi-day effort done while keeping the service running.",
        "source": "https://web.archive.org/web/20230602082218/https://news.ycombinator.com/item?id=1769761"
    },
    {
        "category": "process",
        "company": "Google Cloud",
        "incident": "A Google Cloud customer's GCVE (Google Cloud VMware Engine) private cloud was automatically deleted by Google's systems. The root cause was that the customer's initial provisioning had been done using a legacy option that created an internal billing contract with a fixed term. When the term expired, the automated contract management system interpreted it as a cancellation and deleted all associated resources, including the customer's production VMs and data. Google had no soft-delete or cooling-off period for GCVE resource deletion, and the customer received no warning. Google acknowledged the incident and committed to implementing safeguards.",
        "source": "https://cloud.google.com/blog/products/infrastructure/details-of-google-cloud-gcve-incident"
    },
    {
        "category": "data_loss",
        "company": "Keepthescore",
        "incident": "Engineers at Keepthescore, a small SaaS for tracking scores, accidentally deleted their production PostgreSQL database during a routine maintenance operation. Their backup strategy consisted of daily snapshots taken at midnight. The deletion happened at 7 PM, meaning they lost seven hours of user data — all scoreboards created or updated that day. The backup restoration process itself took several hours because it had never been practiced. The team discovered during recovery that their backup monitoring only checked that the backup job started, not that it completed successfully or that the backup was restorable.",
        "source": "https://web.archive.org/web/20201101133510/https://keepthescore.co/blog/posts/deleting_the_production_database/"
    },
    {
        "category": "security",
        "company": "Homebrew",
        "incident": "A GitHub personal access token for Homebrew's Jenkins CI server was leaked, granting push access to Homebrew's core repository. An attacker could have modified any Homebrew formula to include malicious code, which would then be executed on every macOS developer machine that ran 'brew update.' The token had excessive permissions — it only needed read access to trigger CI builds, but was configured with full write access including push to protected branches. Homebrew had no code signing for formulas, no second-person review requirement for CI-originated commits, and no monitoring for unexpected pushes to protected branches.",
        "source": "https://web.archive.org/web/20210813020247/https://brew.sh/2018/08/05/security-incident-disclosure/"
    },
    {
        "category": "migration",
        "company": "Mandrill/Mailchimp",
        "incident": "Mandrill (Mailchimp's transactional email service) experienced a multi-day partial outage caused by PostgreSQL transaction ID (TXID) wraparound. PostgreSQL uses 32-bit transaction IDs that wrap around after ~4 billion transactions. When a database approaches the wraparound threshold, PostgreSQL forces a safety shutdown to prevent data corruption. Mandrill's vacuum processes (which reclaim old transaction IDs) had fallen behind on several large tables. The team had to manually run VACUUM FREEZE on multi-terabyte tables, a process that took days and consumed significant I/O, causing ongoing performance degradation for customers throughout.",
        "source": "https://mailchimp.com/what-we-learned-from-the-recent-mandrill-outage/"
    },
    {
        "category": "crisis",
        "company": "Datadog",
        "incident": "An automatic Kubernetes node upgrade in Datadog's infrastructure removed all custom network security rules from the nodes. The network rules controlled inter-service communication, database access, and external API connectivity. Without them, services couldn't reach their dependencies, causing a cascading failure across the monitoring platform. The outage lasted 24 hours because restoring the network rules required understanding the dependency graph between services, which wasn't fully documented. The automatic upgrade had been tested in staging, but the staging environment didn't have the same network policy configuration as production.",
        "source": "https://www.datadoghq.com/blog/2023-03-08-multiregion-infrastructure-connectivity-issue/"
    },
    {
        "category": "config_error",
        "company": "Joyent",
        "incident": "An operator at Joyent intended to reboot a specific subset of servers in a datacenter by passing a list to the reboot command. The operator forgot the '-n' flag that would have made the command operate in dry-run mode, and also misspecified the filter, causing the command to target all servers in the US-East-1 availability zone. Every customer VM, including Joyent's own management infrastructure, was rebooted simultaneously. Because the management servers also rebooted, the team couldn't use their normal tools to verify recovery status. They had to physically access the datacenter to restore service, and some customer VMs didn't come back automatically due to dependency ordering issues.",
        "source": "https://web.archive.org/web/20220406095752/https://www.joyent.com/blog/postmortem-for-outage-of-us-east-1-may-27-2014"
    },
    {
        "category": "architecture",
        "company": "Amazon/AWS",
        "incident": "AWS Kinesis experienced a global outage when the front-end fleet exceeded the maximum number of threads allowed by the operating system. A routine capacity scaling operation added new servers to the Kinesis front-end fleet. The new servers triggered a flood of cache-warming requests to existing servers. Each cache-warming connection consumed a thread, and when the thread count hit the OS limit, servers began failing. The failure of some servers caused remaining servers to take on their load, creating a cascading failure. Because CloudWatch, Cognito, and other AWS services depended on Kinesis, the outage cascaded across AWS. The team had to carefully add capacity in small increments to avoid retriggering the cascade.",
        "source": "https://aws.amazon.com/message/11201/"
    },
]

SYSTEM_PROMPT = (
    "You are constructing benchmark tasks for a scientific study of LLM reasoning "
    "across formalization levels. Your job is to transform a real software engineering "
    "incident into a management decision task.\n\n"
    "For the given incident, produce exactly this structure with no other text:\n\n"
    "SCENARIO: [4-6 sentences describing the situation a VP of Engineering or CTO faces, "
    "written in present tense as if the incident just happened. Include the specific "
    "technical details, business context, and constraints from the incident. Do NOT name "
    "the real company — use a plausible fictional name. The scenario must contain all "
    "information needed to reason about the decision.]\n\n"
    "QUESTION: [One clear management decision question. It should require weighing "
    "tradeoffs, considering multiple stakeholders, and proposing concrete actions. "
    "The question must be answerable from the scenario alone.]\n\n"
    "GOLD_ANSWER: [A thorough answer that: (1) identifies the key tradeoffs, "
    "(2) proposes specific actions with reasoning, (3) addresses at least 3 stakeholder "
    "perspectives (engineering, business, customers), and (4) notes what information "
    "would change the recommendation. 150-250 words.]\n\n"
    "COMPLEXITY: [One of: LOW / MEDIUM / HIGH — reflecting how many competing factors "
    "the decision involves]\n\n"
    "STAKEHOLDERS: [Comma-separated list of stakeholder groups affected, e.g.: "
    "engineering team, customers, executive leadership, security team, legal]"
)


def parse_args():
    parser = argparse.ArgumentParser(description="Generate low-formal management decision tasks")
    parser.add_argument("--model", type=str, default=MODEL_DIR)
    parser.add_argument("--max-tasks", type=int, default=len(INCIDENT_SEEDS),
                        help="Maximum number of tasks to generate")
    return parser.parse_args()


def parse_llm_output(raw_text):
    """Parse structured LLM output into fields."""
    result = {
        'scenario': '',
        'question': '',
        'gold_answer': '',
        'complexity': '',
        'stakeholders': '',
    }

    patterns = {
        'scenario': r'SCENARIO:\s*(.+?)(?=\nQUESTION:)',
        'question': r'QUESTION:\s*(.+?)(?=\nGOLD_ANSWER:)',
        'gold_answer': r'GOLD_ANSWER:\s*(.+?)(?=\nCOMPLEXITY:)',
        'complexity': r'COMPLEXITY:\s*(\w+)',
        'stakeholders': r'STAKEHOLDERS:\s*(.+?)(?:\n|$)',
    }

    for field, pattern in patterns.items():
        match = re.search(pattern, raw_text, re.DOTALL)
        if match:
            result[field] = match.group(1).strip()

    # Normalize complexity
    complexity_map = {'LOW': 'simple', 'MEDIUM': 'moderate', 'HIGH': 'complex'}
    result['complexity'] = complexity_map.get(result['complexity'].upper(), result['complexity'].lower()) if result['complexity'] else ''

    return result


def main():
    args = parse_args()
    seeds = INCIDENT_SEEDS[:args.max_tasks]

    print(f"Generating {len(seeds)} management decision tasks from incident postmortems")
    print(f"Categories: {sorted(set(s['category'] for s in seeds))}")

    # Load model
    print(f"\nLoading model: {args.model}")
    model = LocalChatModel(args.model, load_in_4bit=LOAD_IN_4BIT)
    print("Model loaded successfully\n")

    tasks = []
    failed = []

    for idx, seed in enumerate(seeds):
        task_num = idx + 1
        print(f"[{task_num}/{len(seeds)}] {seed['company']} ({seed['category']})...", end=" ", flush=True)

        user_prompt = (
            f"Real incident from a major software company:\n\n"
            f"{seed['incident']}\n\n"
            f"Transform this into a management decision task. "
            f"Do NOT use the real company name — invent a plausible fictional name."
        )

        try:
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            raw_output = model.generate_chat(
                messages, max_new_tokens=768, temperature=0.4
            )

            parsed = parse_llm_output(raw_output)

            if not parsed['scenario'] or not parsed['question'] or not parsed['gold_answer']:
                print("PARTIAL (missing fields)")
                failed.append({'idx': idx, 'company': seed['company'], 'reason': 'missing fields'})
                continue

            tasks.append({
                'id': task_num,
                'category': seed['category'],
                'scenario': parsed['scenario'],
                'question': parsed['question'],
                'gold_answer': parsed['gold_answer'],
                'complexity': parsed['complexity'],
                'stakeholders': parsed['stakeholders'],
                'source': seed['source'],
            })
            print("OK")

        except Exception as e:
            print(f"FAILED ({e})")
            failed.append({'idx': idx, 'company': seed['company'], 'reason': str(e)})

    # Save
    if tasks:
        df_out = pd.DataFrame(tasks)
        df_out['id'] = range(1, len(df_out) + 1)
        OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        df_out.to_csv(OUT_PATH, index=False)
        print(f"\nSaved {len(df_out)} tasks to {OUT_PATH}")
    else:
        print("\nNo tasks generated!")
        return

    # Summary
    print(f"\n{'='*60}")
    print("TASK GENERATION SUMMARY")
    print(f"{'='*60}")
    print(f"Total generated: {len(tasks)}")
    print(f"Failed: {len(failed)}")

    print(f"\nTasks per category:")
    for cat, count in df_out['category'].value_counts().items():
        print(f"  {count:>3}  {cat}")

    print(f"\nComplexity distribution:")
    for level, count in df_out['complexity'].value_counts().items():
        print(f"  {count:>3}  {level}")

    if failed:
        print(f"\nFailed tasks:")
        for f in failed:
            print(f"  {f['company']}: {f['reason']}")


if __name__ == "__main__":
    main()
