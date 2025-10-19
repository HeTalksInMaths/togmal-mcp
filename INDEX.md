# ToGMAL: Taxonomy of Generative Model Apparent Limitations

## 📚 Complete Documentation Index

Welcome to ToGMAL! This index will help you navigate all available documentation.

---

## 🚀 Getting Started (Start Here!)

| Document | Description | When to Read |
|----------|-------------|--------------|
| [**QUICKSTART.md**](./QUICKSTART.md) | 5-minute setup guide | First time setup |
| [**README.md**](./README.md) | Complete feature overview | Understanding capabilities |
| [**DEPLOYMENT.md**](./DEPLOYMENT.md) | Detailed installation guide | Production deployment |

**Recommended order for new users:**
1. QUICKSTART.md → Get running fast
2. README.md → Understand what it does
3. DEPLOYMENT.md → Advanced configuration

---

## 📖 Core Documentation

### [README.md](./README.md)
**Complete user documentation**
- Overview and features
- Installation instructions
- Tool descriptions and parameters
- Detection heuristics explained
- Risk levels and interventions
- Configuration options
- Integration examples

**Best for:** Understanding what ToGMAL does and how to use it

---

### [QUICKSTART.md](./QUICKSTART.md)
**5-minute setup guide**
- Rapid installation
- Quick configuration
- First test examples
- Troubleshooting basics
- Essential usage patterns

**Best for:** Getting started immediately

---

### [DEPLOYMENT.md](./DEPLOYMENT.md)
**Advanced deployment guide**
- Platform-specific setup (macOS/Windows/Linux)
- Claude Desktop integration
- Production deployment strategies
- Performance optimization
- Monitoring and logging
- Security considerations

**Best for:** Production deployments and advanced users

---

## 🏗️ Technical Documentation

### [ARCHITECTURE.md](./ARCHITECTURE.md)
**System design and architecture**
- System overview diagrams
- Component responsibilities
- Data flow visualizations
- Detection pipeline
- Risk calculation algorithm
- Extension points
- Performance characteristics
- Scalability path

**Best for:** Developers and technical understanding

---

### [PROJECT_SUMMARY.md](./PROJECT_SUMMARY.md)
**Project overview and status**
- Feature list
- Implementation details
- Design principles
- Technical specifications
- Future roadmap preview
- Success metrics
- Use cases

**Best for:** Project stakeholders and contributors

---

### [CHANGELOG_ROADMAP.md](./CHANGELOG_ROADMAP.md)
**Version history and future plans**
- Current version features
- Planned enhancements (v1.1, v2.0, v3.0)
- Feature requests
- Technical debt tracking
- Research directions
- Success metrics
- Community contributions

**Best for:** Understanding project evolution and contributing

---

## 💻 Code and Configuration

### [togmal_mcp.py](./togmal_mcp.py)
**Main server implementation**
- 1,270 lines of production code
- 5 MCP tools
- 5 detection heuristics
- Risk assessment system
- Taxonomy database
- Full type hints and documentation

**Best for:** Understanding implementation details

---

### [test_examples.py](./test_examples.py)
**Test cases and examples**
- 10 comprehensive test scenarios
- Expected detection results
- Edge cases
- Borderline examples
- Usage demonstrations

**Best for:** Testing and validation

---

### [requirements.txt](./requirements.txt)
**Python dependencies**
- mcp (MCP SDK)
- pydantic (validation)
- httpx (async HTTP)

**Best for:** Dependency installation

---

### [claude_desktop_config.json](./claude_desktop_config.json)
**Configuration example**
- Claude Desktop integration
- Environment variables
- Server parameters

**Best for:** Configuration reference

---

## 📋 Quick Reference Tables

### Documentation by Task

| Task | Document(s) |
|------|-------------|
| Install for first time | QUICKSTART.md |
| Understand all features | README.md |
| Deploy to production | DEPLOYMENT.md |
| Understand architecture | ARCHITECTURE.md |
| Contribute patterns | README.md + CHANGELOG_ROADMAP.md |
| Troubleshoot issues | DEPLOYMENT.md |
| Extend functionality | ARCHITECTURE.md |
| Check roadmap | CHANGELOG_ROADMAP.md |

### Documentation by Audience

| Audience | Recommended Reading |
|----------|-------------------|
| End Users | QUICKSTART → README |
| Developers | ARCHITECTURE → togmal_mcp.py |
| DevOps | DEPLOYMENT → ARCHITECTURE |
| Contributors | CHANGELOG_ROADMAP → ARCHITECTURE |
| Researchers | PROJECT_SUMMARY → ARCHITECTURE |
| Management | PROJECT_SUMMARY → CHANGELOG_ROADMAP |

### Documentation by Depth

| Level | Documents |
|-------|-----------|
| Quick Overview | QUICKSTART.md (5 min) |
| Basic Understanding | README.md (15 min) |
| Detailed Knowledge | DEPLOYMENT.md + ARCHITECTURE.md (45 min) |
| Complete Mastery | All docs + code review (3+ hours) |

---

## 🎯 Common Use Cases

### Use Case 1: First Time Setup
```
1. Read QUICKSTART.md (5 min)
2. Install dependencies
3. Configure Claude Desktop
4. Test with example prompts
```

### Use Case 2: Understanding Detection
```
1. Read README.md "Detection Heuristics" section
2. Review test_examples.py for examples
3. Check ARCHITECTURE.md for algorithm details
4. Test with your own prompts
```

### Use Case 3: Production Deployment
```
1. Read DEPLOYMENT.md completely
2. Review ARCHITECTURE.md for scale considerations
3. Set up monitoring per DEPLOYMENT.md
4. Configure backups and persistence
5. Test in staging environment
```

### Use Case 4: Contributing
```
1. Read CHANGELOG_ROADMAP.md for priorities
2. Review ARCHITECTURE.md for extension points
3. Study togmal_mcp.py code structure
4. Submit evidence via MCP tool
5. Propose patterns via GitHub
```

### Use Case 5: Research
```
1. Read PROJECT_SUMMARY.md for overview
2. Review ARCHITECTURE.md for methodology
3. Check CHANGELOG_ROADMAP.md for research directions
4. Analyze test_examples.py for scenarios
5. Access taxonomy data via tools
```

---

## 📊 Documentation Statistics

| Metric | Value |
|--------|-------|
| Total Documentation Files | 9 |
| Total Lines of Documentation | ~3,500 |
| Code Files | 2 |
| Total Lines of Code | ~1,400 |
| Test Cases | 10 |
| ASCII Diagrams | 15 |
| Configuration Examples | 3 |

---

## 🔗 File Dependency Graph

```
README.md (start here)
    │
    ├──► QUICKSTART.md (quick setup)
    │        │
    │        └──► togmal_mcp.py (implementation)
    │                 │
    │                 └──► requirements.txt (dependencies)
    │
    ├──► DEPLOYMENT.md (advanced setup)
    │        │
    │        ├──► claude_desktop_config.json (config)
    │        └──► ARCHITECTURE.md (technical details)
    │
    └──► PROJECT_SUMMARY.md (overview)
             │
             └──► CHANGELOG_ROADMAP.md (future plans)
                      │
                      └──► test_examples.py (validation)
```

---

## 🎓 Learning Path

### Beginner Path (2 hours)
1. QUICKSTART.md (15 min)
2. README.md (30 min)
3. test_examples.py review (15 min)
4. Hands-on testing (60 min)

### Intermediate Path (4 hours)
1. Complete Beginner Path
2. DEPLOYMENT.md (45 min)
3. ARCHITECTURE.md overview (30 min)
4. Configuration experimentation (45 min)
5. Custom pattern testing (60 min)

### Advanced Path (8+ hours)
1. Complete Intermediate Path
2. Deep dive into togmal_mcp.py (2 hours)
3. Full ARCHITECTURE.md study (1 hour)
4. CHANGELOG_ROADMAP.md review (30 min)
5. Contribution planning (30 min)
6. Custom detector implementation (3+ hours)

---

## 🔍 Search Tips

### Finding Information

**Installation Issues?**
→ Search DEPLOYMENT.md for your platform or error

**Understanding Detection?**
→ Check README.md heuristics section + ARCHITECTURE.md pipeline

**Configuration Questions?**
→ Look in DEPLOYMENT.md + claude_desktop_config.json

**Want to Contribute?**
→ Read CHANGELOG_ROADMAP.md + ARCHITECTURE.md extensions

**Need Examples?**
→ Check test_examples.py for working code

**Performance Concerns?**
→ Review ARCHITECTURE.md performance section

**Future Features?**
→ Browse CHANGELOG_ROADMAP.md planned features

---

## 📞 Getting Help

### Documentation Issues
- Unclear section? → Note the file and section
- Missing information? → File an issue
- Broken example? → Report with error message

### Technical Support
1. Check DEPLOYMENT.md troubleshooting
2. Review relevant documentation section
3. Search existing GitHub issues
4. File new issue with details

### Contributing
1. Read CHANGELOG_ROADMAP.md priorities
2. Check ARCHITECTURE.md for extension points
3. Follow contribution guidelines
4. Submit PR with documentation updates

---

## 📱 Quick Links

| Resource | Link/Location |
|----------|---------------|
| Main Server | togmal_mcp.py |
| Quick Start | QUICKSTART.md |
| Full Guide | README.md |
| Setup Help | DEPLOYMENT.md |
| Architecture | ARCHITECTURE.md |
| Roadmap | CHANGELOG_ROADMAP.md |
| Examples | test_examples.py |
| Config | claude_desktop_config.json |
| Dependencies | requirements.txt |

---

## ✅ Documentation Coverage

| Topic | Coverage | Documents |
|-------|----------|-----------|
| Installation | ✅ Complete | QUICKSTART, README, DEPLOYMENT |
| Configuration | ✅ Complete | DEPLOYMENT, claude_desktop_config |
| Usage | ✅ Complete | README, test_examples |
| Architecture | ✅ Complete | ARCHITECTURE |
| Contributing | ✅ Complete | CHANGELOG_ROADMAP |
| API Reference | ✅ Complete | README (tool descriptions) |
| Troubleshooting | ✅ Complete | DEPLOYMENT |
| Examples | ✅ Complete | test_examples, README |
| Future Plans | ✅ Complete | CHANGELOG_ROADMAP |
| Performance | ✅ Complete | ARCHITECTURE |

---

## 🎉 You're Ready!

Pick your starting point based on your goal:

- **Quick Start** → QUICKSTART.md
- **Learn Features** → README.md
- **Deploy Production** → DEPLOYMENT.md
- **Understand Code** → ARCHITECTURE.md
- **Plan Future** → CHANGELOG_ROADMAP.md

Happy building with ToGMAL! 🛡️

---

**Last Updated**: October 2025  
**Documentation Version**: 1.0.0  
**Total Files**: 9 documents + 2 code files
