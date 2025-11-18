"""
Error Taxonomy Visualization Tools

Creates visualizations for hierarchical error taxonomy and pattern analysis.
"""

from typing import List, Dict
import json
from pathlib import Path
from collections import Counter

from error_taxonomy import ErrorRecord, ErrorCategory, ErrorSubtype
from error_clustering import ErrorCluster


class ErrorTaxonomyVisualizer:
    """
    Generate visualization-ready data for error taxonomy.
    """

    @staticmethod
    def generate_sunburst_data(errors: List[ErrorRecord]) -> Dict:
        """
        Generate data for sunburst/treemap visualization.

        Format for D3.js, Plotly, or similar libraries.
        """
        root = {
            'name': 'All Errors',
            'children': []
        }

        # Group by category
        for category in ErrorCategory:
            cat_errors = [e for e in errors if e.error_category == category]

            if not cat_errors:
                continue

            category_node = {
                'name': category.value.replace('_', ' ').title(),
                'value': len(cat_errors),
                'children': []
            }

            # Group by subtype
            for subtype in ErrorSubtype:
                sub_errors = [e for e in cat_errors if e.error_subtype == subtype]

                if not sub_errors:
                    continue

                subtype_node = {
                    'name': subtype.value.replace('_', ' ').title(),
                    'value': len(sub_errors)
                }

                category_node['children'].append(subtype_node)

            root['children'].append(category_node)

        return root

    @staticmethod
    def generate_sankey_data(errors: List[ErrorRecord]) -> Dict:
        """
        Generate Sankey diagram data showing error flow:
        Domain → Error Category → Error Subtype
        """
        nodes = []
        links = []
        node_map = {}

        def get_or_create_node(name: str) -> int:
            if name not in node_map:
                node_map[name] = len(nodes)
                nodes.append({'name': name})
            return node_map[name]

        # Create links: domain → category → subtype
        flow_counts = Counter()

        for error in errors:
            domain = error.domain or 'unknown'
            category = error.error_category.value if error.error_category else 'unknown'
            subtype = error.error_subtype.value if error.error_subtype else 'unknown'

            flow_counts[(domain, category)] += 1
            flow_counts[(category, subtype)] += 1

        # Build links
        for (source_name, target_name), count in flow_counts.items():
            source_idx = get_or_create_node(source_name)
            target_idx = get_or_create_node(target_name)

            links.append({
                'source': source_idx,
                'target': target_idx,
                'value': count
            })

        return {
            'nodes': nodes,
            'links': links
        }

    @staticmethod
    def generate_heatmap_data(errors: List[ErrorRecord]) -> Dict:
        """
        Generate heatmap data: Error Type × Domain
        """
        # Build matrix
        domains = sorted(list(set(e.domain for e in errors)))
        subtypes = sorted(list(set(e.error_subtype.value for e in errors
                                   if e.error_subtype)))

        matrix = []

        for subtype in subtypes:
            row = []
            for domain in domains:
                count = len([e for e in errors
                           if e.domain == domain
                           and e.error_subtype
                           and e.error_subtype.value == subtype])
                row.append(count)
            matrix.append(row)

        return {
            'x': domains,  # Domain names
            'y': subtypes,  # Error subtype names
            'z': matrix,  # 2D array of counts
            'type': 'heatmap'
        }

    @staticmethod
    def generate_cluster_scatter_data(
        errors: List[ErrorRecord],
        embeddings: List[List[float]],
        cluster_labels: List[int]
    ) -> Dict:
        """
        Generate 2D scatter plot data for error clusters.

        Assumes embeddings have been reduced to 2D (e.g., via PCA/t-SNE)
        """
        points = []

        for i, error in enumerate(errors):
            if i >= len(embeddings) or i >= len(cluster_labels):
                continue

            points.append({
                'x': embeddings[i][0],
                'y': embeddings[i][1],
                'cluster': cluster_labels[i],
                'domain': error.domain,
                'error_type': error.error_subtype.value if error.error_subtype else 'unknown',
                'question_id': error.question_id,
                'difficulty': error.difficulty_score
            })

        return {
            'points': points,
            'type': 'scatter'
        }

    @staticmethod
    def generate_model_comparison_chart(
        model_profiles: Dict
    ) -> Dict:
        """
        Generate stacked bar chart data comparing models.

        Shows error breakdown by category for each model.
        """
        models = list(model_profiles.keys())
        categories = list(ErrorCategory)

        data = {
            'models': models,
            'categories': [cat.value for cat in categories],
            'series': []
        }

        for category in categories:
            values = []

            for model in models:
                profile = model_profiles[model]
                count = profile.errors_by_category.get(category, 0)
                values.append(count)

            data['series'].append({
                'name': category.value,
                'values': values
            })

        return data

    @staticmethod
    def export_for_plotly(
        errors: List[ErrorRecord],
        output_path: str
    ) -> None:
        """
        Export visualization data in Plotly-compatible JSON format.
        """
        viz_data = {
            'sunburst': ErrorTaxonomyVisualizer.generate_sunburst_data(errors),
            'sankey': ErrorTaxonomyVisualizer.generate_sankey_data(errors),
            'heatmap': ErrorTaxonomyVisualizer.generate_heatmap_data(errors)
        }

        with open(output_path, 'w') as f:
            json.dump(viz_data, f, indent=2)

    @staticmethod
    def generate_html_dashboard(
        errors: List[ErrorRecord],
        clusters: List[ErrorCluster],
        model_profiles: Dict,
        output_path: str
    ) -> None:
        """
        Generate simple HTML dashboard with embedded visualizations.
        """
        html = """
<!DOCTYPE html>
<html>
<head>
    <title>LLM Error Taxonomy Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }
        h2 {
            color: #555;
            margin-top: 40px;
        }
        .chart {
            margin: 20px 0;
            height: 500px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .stat-card {
            background: #f9f9f9;
            padding: 20px;
            border-radius: 4px;
            border-left: 4px solid #4CAF50;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: #4CAF50;
        }
        .stat-label {
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 LLM Error Taxonomy Analysis</h1>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">""" + str(len(errors)) + """</div>
                <div class="stat-label">Total Errors</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + str(len(set(e.question_id for e in errors))) + """</div>
                <div class="stat-label">Unique Questions</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + str(len(set(e.model_name for e in errors))) + """</div>
                <div class="stat-label">Models Tested</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">""" + str(len(clusters)) + """</div>
                <div class="stat-label">Error Patterns</div>
            </div>
        </div>

        <h2>Error Taxonomy Hierarchy</h2>
        <div id="sunburst" class="chart"></div>

        <h2>Error Flow: Domain → Category → Subtype</h2>
        <div id="sankey" class="chart"></div>

        <h2>Error Distribution Heatmap</h2>
        <div id="heatmap" class="chart"></div>

        <script>
            // Sunburst chart
            var sunburstData = """ + json.dumps(ErrorTaxonomyVisualizer.generate_sunburst_data(errors)) + """;

            Plotly.newPlot('sunburst', [{
                type: 'sunburst',
                labels: getAllLabels(sunburstData),
                parents: getAllParents(sunburstData),
                values: getAllValues(sunburstData),
                textinfo: 'label+percent parent',
                hovertemplate: '<b>%{label}</b><br>Errors: %{value}<br>%{percentParent}<extra></extra>',
                marker: {
                    colorscale: 'Viridis'
                }
            }], {
                margin: {l: 0, r: 0, t: 0, b: 0},
                height: 500
            });

            function getAllLabels(node, labels = [], parent = '') {
                labels.push(node.name);
                if (node.children) {
                    node.children.forEach(child => getAllLabels(child, labels, node.name));
                }
                return labels;
            }

            function getAllParents(node, parents = [], parent = '') {
                parents.push(parent);
                if (node.children) {
                    node.children.forEach(child => getAllParents(child, parents, node.name));
                }
                return parents;
            }

            function getAllValues(node, values = []) {
                values.push(node.value || 0);
                if (node.children) {
                    node.children.forEach(child => getAllValues(child, values));
                }
                return values;
            }

            // Sankey chart
            var sankeyData = """ + json.dumps(ErrorTaxonomyVisualizer.generate_sankey_data(errors)) + """;

            Plotly.newPlot('sankey', [{
                type: 'sankey',
                node: {
                    label: sankeyData.nodes.map(n => n.name),
                    color: 'rgba(76, 175, 80, 0.8)'
                },
                link: {
                    source: sankeyData.links.map(l => l.source),
                    target: sankeyData.links.map(l => l.target),
                    value: sankeyData.links.map(l => l.value),
                    color: 'rgba(0, 0, 0, 0.2)'
                }
            }], {
                margin: {l: 0, r: 0, t: 0, b: 0},
                height: 500
            });

            // Heatmap
            var heatmapData = """ + json.dumps(ErrorTaxonomyVisualizer.generate_heatmap_data(errors)) + """;

            Plotly.newPlot('heatmap', [{
                z: heatmapData.z,
                x: heatmapData.x,
                y: heatmapData.y,
                type: 'heatmap',
                colorscale: 'Greens',
                hoverongaps: false,
                hovertemplate: 'Domain: %{x}<br>Error Type: %{y}<br>Count: %{z}<extra></extra>'
            }], {
                xaxis: {title: 'Domain'},
                yaxis: {title: 'Error Type'},
                height: 500
            });
        </script>
    </div>
</body>
</html>
        """

        with open(output_path, 'w') as f:
            f.write(html)


def generate_all_visualizations(
    errors: List[ErrorRecord],
    clusters: List[ErrorCluster],
    model_profiles: Dict,
    output_dir: str = "data/error_analysis_results"
) -> None:
    """
    Generate all visualization outputs.
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    viz = ErrorTaxonomyVisualizer()

    # Export Plotly data
    viz.export_for_plotly(
        errors,
        str(output_path / "plotly_data.json")
    )

    # Generate HTML dashboard
    viz.generate_html_dashboard(
        errors,
        clusters,
        model_profiles,
        str(output_path / "dashboard.html")
    )

    print(f"Visualizations generated in {output_path}/")
    print(f"  - plotly_data.json: Data for custom Plotly charts")
    print(f"  - dashboard.html: Interactive HTML dashboard")
