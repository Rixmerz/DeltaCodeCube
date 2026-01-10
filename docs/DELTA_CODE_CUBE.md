# DeltaCodeCube - Sistema de Indexación Multidimensional para Código

## Resumen Ejecutivo

DeltaCodeCube es una extensión de bigcontext-mcp que representa código fuente como puntos en un espacio tridimensional, permitiendo:

1. **Búsqueda multidimensional**: Encontrar código similar en estructura, semántica o léxico
2. **Detección de impacto de cambios**: Predecir qué archivos se afectan cuando uno cambia
3. **Automatización de contratos**: Detectar cuándo cambios rompen dependencias implícitas

---

## Inspiración: DVC Cúbico Diferencial (EVA4)

Basado en el proyecto [EVA4-Machine-Learning](../../../EVA4-Machine-Learning), que implementa versionamiento volumétrico:

```
L₀  = Capa base (estado inicial)
Δₙ = Lₙ - Lₙ₋₁ (delta incremental)

Reconstrucción: Lₙ = L₀ + Δ₁ + Δ₂ + ... + Δₙ
```

### Adaptación para Código

En lugar de versiones temporales, los "deltas" representan **diferentes dimensiones de análisis** del mismo código:

```
Código → [Lexical, Structural, Semantic] → Punto en Cubo 3D
```

---

## Arquitecturas Alternativas Evaluadas

Durante el diseño se evaluaron 3 arquitecturas diferentes para aplicar el concepto de "cubo diferencial" a la indexación de código. A continuación se documenta cada una con sus ventajas, desventajas y razones de elección.

### Arquitectura A: Deltas como Niveles de Abstracción Jerárquica

**Concepto**: Representar el código en capas incrementales de abstracción, donde cada delta agrega un nivel de agrupación.

```
L₀  = Base (Tokens individuales)
     │
     ▼ Δ₁ (agrupación)
L₁  = Statements (líneas de código)
     │
     ▼ Δ₂ (agrupación)
L₂  = Functions (bloques funcionales)
     │
     ▼ Δ₃ (agrupación)
L₃  = Modules (archivos completos)
     │
     ▼ Δ₄ (agrupación)
L₄  = Domains (clustering semántico)

Fórmula: Abstracción_n = Base + Σ(Δᵢ) donde cada Δ agrega información de agrupación
```

#### Implementación Conceptual

```python
class CodeAbstractionCube:
    """
    Sistema de indexación por niveles de abstracción.
    """
    def __init__(self, codebase):
        # Capa base: tokens individuales
        self.base = TokenIndex(codebase)      # TF-IDF de términos

        # Deltas como niveles de abstracción
        self.deltas = [
            StatementDelta(),   # Δ₁: agrupa tokens → statements
            FunctionDelta(),    # Δ₂: agrupa statements → funciones
            ModuleDelta(),      # Δ₃: agrupa funciones → módulos
            DomainDelta(),      # Δ₄: clustering semántico (auth, db, ui, etc)
        ]

    def search(self, query, level="auto"):
        """
        Busca en un nivel específico o en todos.

        Args:
            query: Texto de búsqueda
            level: 0=tokens, 1=statements, 2=functions, 3=modules, 4=domains, "auto"=todos
        """
        if level == "auto":
            # Busca en todos los niveles, pondera resultados por varianza
            return self._multi_level_search(query)

        # Reconstruir nivel específico
        abstraction = self._reconstruct_level(level)
        return abstraction.search(query)

    def _reconstruct_level(self, n):
        """Reconstruye nivel n: Base + Δ₁ + Δ₂ + ... + Δₙ"""
        result = self.base.copy()
        for i in range(n):
            result = result + self.deltas[i]
        return result
```

#### Ejemplo de Búsqueda Multi-Nivel

```
Query: "validate user authentication"

Nivel 0 (Tokens):
  - Encuentra: "validate", "user", "auth" en 50 ubicaciones
  - Muy granular, muchos falsos positivos

Nivel 1 (Statements):
  - Encuentra: if (validateUser(auth)) en 15 líneas
  - Más específico

Nivel 2 (Functions):
  - Encuentra: function validateUserAuth() {} en 3 funciones
  - Contexto funcional

Nivel 3 (Modules):
  - Encuentra: auth.js, middleware/session.js
  - Contexto de archivo

Nivel 4 (Domains):
  - Encuentra: todo el dominio "auth"
  - Máxima abstracción

Resultado Auto: Pondera y combina niveles 2-3 (balance entre precisión y contexto)
```

#### Ventajas

✅ **Elegancia conceptual**: Aprovecha jerarquía natural del código (tokens → statements → funciones → módulos)

✅ **Flexibilidad de consulta**: Usuario puede elegir nivel de detalle deseado

✅ **Navegación natural**: Fácil "zoom in/out" entre niveles de abstracción

✅ **Alineado con comprensión humana**: Los desarrolladores piensan en estos niveles

#### Desventajas

❌ **Complejidad de implementación**: Requiere AST parsing robusto para detectar boundaries (statements, funciones)

❌ **Dependencia de lenguaje**: AST diferente por lenguaje (JS, Python, Go, etc)

❌ **Costo computacional**: Construir jerarquía completa es costoso

❌ **Ambigüedad en deltas**: ¿Qué es un "statement" en código sin puntos y comas (Python)? ¿Lambdas son funciones?

#### Decisión

**No seleccionada para v1** - Reservada para v2 si se justifica la complejidad de AST parsing completo.

---

### Arquitectura B: Multi-Motor Paralelo (No-Diferencial)

**Concepto**: Múltiples índices independientes (no deltas), cada uno especializado en un tipo de búsqueda. Resultados se fusionan con pesos.

```
                    Query: "validate email"
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼─────┐      ┌──────▼──────┐      ┌────▼─────┐
   │  Motor   │      │   Motor     │      │  Motor   │
   │  TF-IDF  │      │    AST      │      │  Graph   │
   │          │      │             │      │          │
   │ (lexical)│      │(structural) │      │ (deps)   │
   └────┬─────┘      └──────┬──────┘      └────┬─────┘
        │                   │                   │
        │  Score: 0.8       │  Score: 0.6       │  Score: 0.9
        │                   │                   │
        └───────────────────┼───────────────────┘
                            │
                   ┌────────▼─────────┐
                   │  Hybrid Merger   │
                   │  w₁·s₁ + w₂·s₂  │
                   │    + w₃·s₃      │
                   └────────┬─────────┘
                            │
                      Results Ranked
```

#### Implementación Conceptual

```python
class MultiEngineCodeSearch:
    """
    Búsqueda con múltiples motores independientes.
    """
    def __init__(self, codebase):
        # Cada motor indexa TODO el código de forma independiente
        self.engines = {
            'lexical': TFIDFEngine(codebase),        # Términos
            'structural': ASTEngine(codebase),        # Estructura sintáctica
            'semantic': EmbeddingEngine(codebase),    # Embeddings (OpenAI/local)
            'graph': DependencyEngine(codebase),      # Grafo de imports
        }

        # Pesos por defecto (ajustables por usuario)
        self.weights = {
            'lexical': 0.3,
            'structural': 0.2,
            'semantic': 0.3,
            'graph': 0.2,
        }

    def search(self, query, engines=None, weights=None):
        """
        Busca con motores seleccionados y fusiona resultados.
        """
        engines = engines or list(self.engines.keys())
        weights = weights or self.weights

        # Ejecutar búsquedas en paralelo
        results = {}
        for engine_name in engines:
            results[engine_name] = self.engines[engine_name].search(query)

        # Fusionar resultados con pesos
        return self._merge_results(results, weights)

    def _merge_results(self, results, weights):
        """
        Fusión por scoring ponderado.

        Para cada archivo, score final = Σ(weight_i × score_i)
        """
        merged = defaultdict(float)

        for engine, engine_results in results.items():
            w = weights[engine]
            for file_path, score in engine_results:
                merged[file_path] += w * score

        # Ordenar por score descendente
        return sorted(merged.items(), key=lambda x: x[1], reverse=True)
```

#### Ejemplo de Búsqueda

```
Query: "authentication middleware"

Motor Lexical (TF-IDF):
  1. auth.js (score: 0.85) - tiene ambos términos
  2. middleware.js (score: 0.72)
  3. session.js (score: 0.43)

Motor Structural (AST):
  1. middleware.js (score: 0.91) - tiene patrón middleware
  2. auth.js (score: 0.54)
  3. api.js (score: 0.33)

Motor Semantic (Embeddings):
  1. auth.js (score: 0.88) - dominio auth
  2. session.js (score: 0.79) - relacionado
  3. middleware.js (score: 0.61)

Motor Graph (Dependencies):
  1. auth.js (score: 0.95) - hub de dependencias
  2. middleware.js (score: 0.72)
  3. api.js (score: 0.44)

Fusión (w_lex=0.3, w_struct=0.2, w_sem=0.3, w_graph=0.2):
  1. auth.js (0.805) ← mejor combinación
  2. middleware.js (0.705)
  3. session.js (0.498)
```

#### Ventajas

✅ **Simplicidad arquitectónica**: Cada motor es independiente, más fácil de mantener

✅ **Paralelización**: Búsquedas pueden ejecutarse en paralelo

✅ **Modularidad**: Agregar/quitar motores sin afectar otros

✅ **Flexibilidad**: Usuario controla qué motores usar y con qué pesos

✅ **Sin dependencias entre motores**: Fallos aislados

#### Desventajas

❌ **Redundancia de almacenamiento**: Cada motor indexa TODO el código

❌ **No aprovecha concepto de deltas**: No es un "cubo diferencial" realmente

❌ **Tunning de pesos complejo**: Difícil encontrar pesos óptimos

❌ **Escalabilidad**: N motores = N veces el espacio de almacenamiento

❌ **Menos innovador**: Approach común (Elasticsearch, etc)

#### Decisión

**No seleccionada** - Aunque simple, no aprovecha la innovación del concepto de "cubo diferencial" de EVA4. Es un sistema multi-índice tradicional.

---

### Arquitectura C: Cubo 3D de Features (SELECCIONADA)

**Concepto**: Representar cada archivo como un punto en espacio 3D (Lexical, Structural, Semantic). Los deltas capturan movimiento cuando el código cambia.

```
                     Semantic (Z)
                         │
                         │   ┌─────────────┐
                         │  /  dashboard  /│
                         │ /   .js       /─┼────► Structural (Y)
                         │/─────────────/  │      (complexity, LOC, imports)
                         │               │
        auth.js ●────────┼────────●      │
                         │     api.js    │
                        /                │
                       /                 │
        Lexical (X) ◄──────────────────────────┘
        (TF-IDF scores)


        DELTA cuando auth.js cambia:

        Antes: auth.js @ (0.3, 0.5, 0.8)
        Después: auth.js @ (0.3, 0.7, 0.8)  ← movimiento en Y (structural)

        Delta = (0.0, +0.2, 0.0)
        → Cambio principalmente ESTRUCTURAL
```

#### Implementación Conceptual

```python
class DeltaCodeCube:
    """
    Cubo 3D donde código = punto, cambios = deltas.
    """
    def __init__(self, codebase):
        self.code_points = {}  # {file_path: CodePoint}
        self.deltas = []       # Historial de movimientos
        self.contracts = []    # Grafo de dependencias

        # Indexar todo el código
        for file_path in codebase:
            self.code_points[file_path] = self._build_code_point(file_path)

        # Detectar contratos (imports)
        self._detect_contracts()

    def _build_code_point(self, file_path):
        """
        Construye punto 3D para un archivo.

        Returns:
            CodePoint con position = [lexical (50d), structural (8d), semantic (5d)]
        """
        content = read_file(file_path)

        return CodePoint(
            file_path=file_path,
            lexical=extract_lexical_features(content),      # [50 dims]
            structural=extract_structural_features(content), # [8 dims]
            semantic=extract_semantic_features(content),     # [5 dims]
        )

    def on_file_change(self, file_path, new_content):
        """
        Detecta impacto de cambio en un archivo.
        """
        # 1. Calcular nuevo CodePoint
        old_point = self.code_points[file_path]
        new_point = self._build_code_point_from_content(file_path, new_content)

        # 2. Crear Delta
        delta = Delta(
            code_point_id=file_path,
            old_position=old_point.position,
            new_position=new_point.position,
            movement=new_point.position - old_point.position,
            magnitude=np.linalg.norm(new_point.position - old_point.position),
        )

        # 3. Detectar tensiones en contratos
        tensions = self._detect_tensions(old_point, new_point, delta)

        # 4. Actualizar
        self.code_points[file_path] = new_point
        self.deltas.append(delta)

        return TensionReport(delta=delta, tensions=tensions)

    def _detect_tensions(self, old_point, new_point, delta):
        """
        Detecta contratos rotos por el cambio.

        Tensión = |nueva_distancia - baseline_distancia|
        """
        tensions = []

        # Buscar contratos donde este archivo es callee
        for contract in self.contracts:
            if contract.callee_id == old_point.file_path:
                caller = self.code_points[contract.caller_id]

                new_distance = caller.distance_to(new_point)
                tension_magnitude = abs(new_distance - contract.baseline_distance)

                if tension_magnitude > THRESHOLD:
                    tensions.append(Tension(
                        contract=contract,
                        delta=delta,
                        magnitude=tension_magnitude,
                    ))

        return tensions

    def search(self, query, axis=None):
        """
        Búsqueda por similaridad en el cubo.

        Args:
            query: Texto o CodePoint de referencia
            axis: 'lexical', 'structural', 'semantic', None (todos)
        """
        query_point = self._query_to_code_point(query)

        results = []
        for file_path, code_point in self.code_points.items():
            if axis:
                # Distancia solo en eje específico
                distance = self._distance_in_axis(query_point, code_point, axis)
            else:
                # Distancia euclidiana completa
                distance = query_point.distance_to(code_point)

            results.append((file_path, distance))

        # Ordenar por distancia (menor = más similar)
        return sorted(results, key=lambda x: x[1])
```

#### Ventajas

✅ **Innovador**: Aprovecha concepto de cubo diferencial de EVA4

✅ **Detección predictiva de impacto**: Predice qué se rompe ANTES de que compile

✅ **Queries complejas**: "Similar en estructura pero diferente en semántica"

✅ **Visualizable**: Puede exportarse a 3D para visualización

✅ **Balance complejidad/valor**: No requiere AST completo pero aporta valor único

✅ **Extensible**: Fácil agregar más dimensiones (security, performance, etc)

#### Desventajas

⚠️ **Requiere tunning**: Threshold de tensión, pesos de features

⚠️ **Features heurísticas**: Sin AST, structural features son aproximadas

⚠️ **Experimental**: No hay herramientas existentes para comparar

⚠️ **Falsos positivos**: Puede detectar tensiones en cambios benignos

#### Decisión

**✅ SELECCIONADA** - Mejor balance entre innovación, complejidad de implementación y valor aportado. Permite empezar simple (sin AST) y evolucionar.

---

## Comparación de Arquitecturas

| Criterio | Arquitectura A (Jerarquías) | Arquitectura B (Multi-Motor) | Arquitectura C (Cubo 3D) ✅ |
|----------|----------------------------|----------------------------|---------------------------|
| **Innovación** | Alta | Baja | Muy Alta |
| **Complejidad implementación** | Alta (AST necesario) | Media | Media |
| **Dependencias externas** | AST parser | Múltiples | Mínimas |
| **Concepto diferencial** | ✅ Sí | ❌ No | ✅ Sí |
| **Detección de impacto** | Limitada | No | ✅ Excelente |
| **Escalabilidad** | Media | Baja (N índices) | Alta |
| **Extensibilidad** | Media | Alta | Alta |
| **Multi-lenguaje** | Difícil (N parsers) | Media | ✅ Fácil |
| **Visualización** | Jerárquica | No natural | ✅ 3D intuitivo |

---

## Evolución Futura

### Fase 2: Combinar A + C

Posible evolución que combine lo mejor de ambas:

```
DeltaCodeCube v2:

Eje X: Lexical (TF-IDF)
Eje Y: Structural (desde features heurísticas)
Eje Z: Semantic (dominios)

PLUS:

Eje W (4D): Hierarchical Level
  - 0 = Token
  - 1 = Statement
  - 2 = Function
  - 3 = Module
  - 4 = Domain

→ Búsqueda en hipercubo 4D con filtros por nivel jerárquico
```

Esto requeriría AST parsing pero mantendría beneficios del cubo 3D.

---

## Arquitectura del Sistema

### Vista General

```
┌─────────────────────────────────────────────────────────────────────┐
│                        DeltaCodeCube                                 │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CAPA 1: FEATURE EXTRACTION                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────────┐  │
│  │  LEXICAL (X)     │  │  STRUCTURAL (Y)  │  │  SEMANTIC (Z)     │  │
│  │  50 dimensiones  │  │  8 dimensiones   │  │  5 dimensiones    │  │
│  └────────┬─────────┘  └────────┬─────────┘  └─────────┬─────────┘  │
│           └─────────────────────┼──────────────────────┘            │
│                                 ▼                                    │
│  CAPA 2: CODE POINTS                                                 │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  CodePoint = vector de 63 dimensiones                           │ │
│  │  Cada archivo/función = un punto en el espacio                  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                    │
│  CAPA 3: CONTRACTS                                                   │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Grafo de dependencias entre CodePoints                         │ │
│  │  Baseline distance = distancia "saludable" entre caller/callee  │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                    │
│  CAPA 4: TENSION DETECTION                                           │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │  Cuando un archivo cambia → detectar contratos rotos            │ │
│  │  Tensión = |nueva_distancia - baseline_distance|                │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Componentes Detallados

### 1. Feature Extraction

#### 1.1 Lexical Features (Eje X) - 50 dimensiones

Basado en TF-IDF existente en bigcontext-mcp.

```python
def extract_lexical_features(content: str, global_vocab: list[str]) -> np.ndarray:
    """
    Extrae features léxicas usando TF-IDF proyectado.

    - Calcula TF-IDF de todos los términos
    - Proyecta a vocabulario global (top 50 términos del corpus)
    - Normaliza el vector resultante

    Returns:
        Vector de 50 dimensiones normalizado
    """
```

**Qué captura**: Terminología, naming conventions, keywords del dominio.

**Ejemplo**: Un archivo con muchos términos como `user`, `auth`, `token` estará cerca de otros archivos de autenticación en el eje X.

#### 1.2 Structural Features (Eje Y) - 8 dimensiones

Features extraídas con regex/heurísticas (sin AST pesado).

| Feature | Descripción | Normalización |
|---------|-------------|---------------|
| `loc` | Líneas de código | `/500` (max 1.0) |
| `num_functions` | Cantidad de funciones | `/20` |
| `num_classes` | Cantidad de clases | `/10` |
| `num_imports` | Cantidad de imports | `/30` |
| `avg_indent` | Indentación promedio | `/4` (tabs) |
| `comment_ratio` | Ratio comentarios/código | directo |
| `cyclomatic_estimate` | Complejidad estimada | `/100` |
| `export_count` | Cantidad de exports | `/15` |

```python
def extract_structural_features(content: str, extension: str) -> np.ndarray:
    """
    Extrae features estructurales sin parser AST.

    Usa patrones regex para detectar:
    - Definiciones de funciones (function, def, =>)
    - Clases (class)
    - Imports (import, require, from...import)
    - Exports (export, module.exports)

    Returns:
        Vector de 8 dimensiones normalizado
    """
```

**Qué captura**: Complejidad, tamaño, modularidad del código.

**Ejemplo**: Un archivo con muchas funciones pequeñas vs uno con pocas funciones largas tendrán posiciones diferentes en Y.

#### 1.3 Semantic Features (Eje Z) - 5 dimensiones

Clasificación por dominio funcional usando keywords.

| Dominio | Keywords de ejemplo |
|---------|---------------------|
| `auth` | login, password, token, session, user, auth, jwt, credential |
| `db` | query, select, insert, database, model, schema, migration, table |
| `api` | route, endpoint, request, response, http, rest, controller, handler |
| `ui` | render, component, view, style, click, button, form, input |
| `util` | helper, util, format, parse, convert, validate, transform |

```python
def extract_semantic_features(content: str) -> np.ndarray:
    """
    Clasifica el código por dominio funcional.

    Cuenta ocurrencias de keywords por dominio y normaliza
    a distribución de probabilidad.

    Returns:
        Vector de 5 dimensiones (suma = 1.0)
    """
```

**Qué captura**: Propósito funcional del código.

**Ejemplo**: `auth.js` tendrá alto valor en dimensión `auth`, `database.js` en dimensión `db`.

---

### 2. CodePoint

Representación de una unidad de código (archivo o función) como punto en el cubo.

```python
@dataclass
class CodePoint:
    # Identificación
    id: str                      # Unique ID
    file_path: str               # Ruta al archivo
    function_name: str | None    # Nombre de función (si aplica)

    # Coordenadas en el cubo (63 dimensiones total)
    lexical: np.ndarray          # [50] TF-IDF features
    structural: np.ndarray       # [8] Structural features
    semantic: np.ndarray         # [5] Domain features

    # Metadata
    content_hash: str            # SHA256 del contenido
    created_at: datetime
    updated_at: datetime

    @property
    def position(self) -> np.ndarray:
        """Vector completo de 63 dimensiones."""
        return np.concatenate([self.lexical, self.structural, self.semantic])

    def distance_to(self, other: 'CodePoint') -> float:
        """Distancia euclidiana a otro CodePoint."""
        return np.linalg.norm(self.position - other.position)
```

---

### 3. Contracts (Contratos)

Relación de dependencia entre dos CodePoints con distancia baseline.

```python
@dataclass
class Contract:
    id: str
    caller_id: str              # CodePoint que importa/usa
    callee_id: str              # CodePoint que es importado/usado
    contract_type: str          # 'import', 'function_call', 'inheritance'

    baseline_distance: float    # Distancia "saludable" cuando se creó

    created_at: datetime

    def calculate_tension(self, cube: 'DeltaCodeCube') -> float:
        """Calcula tensión actual vs baseline."""
        caller = cube.get_code_point(self.caller_id)
        callee = cube.get_code_point(self.callee_id)
        current_distance = caller.distance_to(callee)
        return abs(current_distance - self.baseline_distance)
```

#### Detección de Contratos

```python
def detect_contracts(content: str, file_path: str, all_files: dict) -> list[Contract]:
    """
    Detecta imports y referencias a otros archivos usando regex.

    Patterns soportados:
    - ES6: import X from './path'
    - CommonJS: require('./path')
    - Python: from module import X
    """
    patterns = [
        r"import\s+.*?from\s+['\"](.+?)['\"]",    # ES6
        r"require\s*\(\s*['\"](.+?)['\"]",         # CommonJS
        r"from\s+(\S+)\s+import",                  # Python
    ]
    # ... detectar y resolver paths
```

---

### 4. Delta

Registro de movimiento de un CodePoint cuando su código cambia.

```python
@dataclass
class Delta:
    id: str
    code_point_id: str

    old_position: np.ndarray    # Posición anterior (63 dims)
    new_position: np.ndarray    # Posición nueva (63 dims)

    movement: np.ndarray        # new - old
    magnitude: float            # ||movement||

    # Análisis del movimiento
    lexical_change: float       # Cambio en dimensiones léxicas
    structural_change: float    # Cambio en dimensiones estructurales
    semantic_change: float      # Cambio en dimensiones semánticas
    dominant_change: str        # 'lexical', 'structural', o 'semantic'

    created_at: datetime
```

---

### 5. Tension (Tensión)

Indica que un contrato puede estar roto después de un cambio.

```python
@dataclass
class Tension:
    id: str
    contract_id: str
    delta_id: str               # Delta que causó la tensión

    tension_magnitude: float    # |current_distance - baseline|

    status: str                 # 'detected', 'reviewed', 'resolved', 'ignored'

    # Información para el desarrollador
    caller_file: str
    callee_file: str
    likely_affected_lines: list[int]
    suggested_action: str

    created_at: datetime
```

---

## Flujo de Operación

### Flujo 1: Indexación Inicial

```
1. Usuario ejecuta: cube_index_project("/path/to/project")

2. Para cada archivo de código:
   a. Parsear contenido
   b. Extraer features [lexical, structural, semantic]
   c. Crear CodePoint
   d. Guardar en DB

3. Detectar contratos (imports entre archivos)
   a. Para cada archivo, buscar imports
   b. Resolver paths relativos
   c. Calcular baseline_distance
   d. Guardar Contract en DB

4. Retornar estadísticas:
   - N archivos indexados
   - M contratos detectados
   - Distribución en el cubo
```

### Flujo 2: Detección de Impacto (on change)

```
1. Usuario modifica auth.js y ejecuta: cube_analyze_impact("auth.js")

2. Sistema:
   a. Leer nuevo contenido de auth.js
   b. Calcular nuevo CodePoint
   c. Comparar con CodePoint anterior → crear Delta

3. Buscar contratos donde auth.js es callee:
   - api.js → auth.js (Contract #1)
   - middleware.js → auth.js (Contract #2)
   - test.js → auth.js (Contract #3)

4. Para cada contrato:
   a. Calcular nueva distancia caller↔auth.js
   b. Comparar con baseline_distance
   c. Si diferencia > threshold → crear Tension

5. Retornar TensionReport:
   - Delta del archivo modificado
   - Lista de tensiones detectadas
   - Archivos NO afectados (distancia estable)
```

### Flujo 3: Búsqueda por Similaridad

```
1. Usuario ejecuta: cube_find_similar("auth.js", limit=5)

2. Sistema:
   a. Obtener CodePoint de auth.js
   b. Calcular distancia a todos los demás CodePoints
   c. Ordenar por distancia ascendente
   d. Retornar top-5 más cercanos

3. Opciones avanzadas:
   - Buscar similares solo en eje X (léxico)
   - Buscar similares solo en eje Y (estructura)
   - Buscar similares solo en eje Z (semántica)
   - Buscar "opuestos" (máxima distancia en un eje, mínima en otros)
```

---

## Esquema de Base de Datos

```sql
-- Puntos de código en el cubo 3D
CREATE TABLE code_points (
    id TEXT PRIMARY KEY,
    file_path TEXT NOT NULL UNIQUE,
    function_name TEXT,

    -- Features (almacenadas como JSON)
    lexical_features TEXT NOT NULL,      -- JSON array [50 floats]
    structural_features TEXT NOT NULL,   -- JSON array [8 floats]
    semantic_features TEXT NOT NULL,     -- JSON array [5 floats]

    -- Metadata
    content_hash TEXT NOT NULL,
    line_count INTEGER,

    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Contratos (dependencias) entre code points
CREATE TABLE contracts (
    id TEXT PRIMARY KEY,
    caller_id TEXT NOT NULL REFERENCES code_points(id) ON DELETE CASCADE,
    callee_id TEXT NOT NULL REFERENCES code_points(id) ON DELETE CASCADE,
    contract_type TEXT NOT NULL CHECK (contract_type IN ('import', 'call', 'inherit')),

    baseline_distance REAL NOT NULL,

    created_at TEXT DEFAULT (datetime('now')),

    UNIQUE(caller_id, callee_id)
);

-- Historial de cambios (deltas)
CREATE TABLE deltas (
    id TEXT PRIMARY KEY,
    code_point_id TEXT NOT NULL REFERENCES code_points(id) ON DELETE CASCADE,

    old_position TEXT NOT NULL,          -- JSON array [63 floats]
    new_position TEXT NOT NULL,          -- JSON array [63 floats]

    movement_magnitude REAL NOT NULL,
    lexical_change REAL NOT NULL,
    structural_change REAL NOT NULL,
    semantic_change REAL NOT NULL,
    dominant_change TEXT NOT NULL,

    created_at TEXT DEFAULT (datetime('now'))
);

-- Tensiones detectadas
CREATE TABLE tensions (
    id TEXT PRIMARY KEY,
    contract_id TEXT NOT NULL REFERENCES contracts(id) ON DELETE CASCADE,
    delta_id TEXT NOT NULL REFERENCES deltas(id) ON DELETE CASCADE,

    tension_magnitude REAL NOT NULL,
    status TEXT NOT NULL DEFAULT 'detected'
        CHECK (status IN ('detected', 'reviewed', 'resolved', 'ignored')),

    suggested_action TEXT,

    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
);

-- Índices para performance
CREATE INDEX idx_code_points_path ON code_points(file_path);
CREATE INDEX idx_contracts_caller ON contracts(caller_id);
CREATE INDEX idx_contracts_callee ON contracts(callee_id);
CREATE INDEX idx_deltas_code_point ON deltas(code_point_id);
CREATE INDEX idx_tensions_status ON tensions(status);
```

---

## Herramientas MCP Propuestas

### Herramientas de Indexación

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `cube_index_file` | Indexa un archivo individual | `path`, `force` |
| `cube_index_directory` | Indexa todos los archivos de código en un directorio | `path`, `recursive`, `patterns` |
| `cube_reindex` | Re-indexa archivo existente y detecta tensiones | `path` |

### Herramientas de Consulta

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `cube_get_position` | Obtiene posición de un archivo en el cubo | `path` |
| `cube_find_similar` | Encuentra archivos similares | `path`, `limit`, `axis` |
| `cube_get_contracts` | Lista contratos de un archivo | `path`, `direction` |
| `cube_compare` | Compara dos archivos en el cubo | `path_a`, `path_b` |

### Herramientas de Análisis

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `cube_analyze_impact` | Analiza impacto de cambios en un archivo | `path` |
| `cube_get_tensions` | Lista tensiones no resueltas | `status`, `limit` |
| `cube_resolve_tension` | Marca tensión como resuelta | `tension_id`, `status` |

### Herramientas de Visualización

| Tool | Descripción | Parámetros |
|------|-------------|------------|
| `cube_export_positions` | Exporta posiciones para visualización externa | `format` |
| `cube_get_stats` | Estadísticas del cubo | - |

---

## Casos de Uso

### Caso 1: Encontrar código relacionado

```
Usuario: "¿Qué archivos son similares a auth.js?"

> cube_find_similar path=/src/services/auth.js limit=5

Resultado:
1. /src/middleware/session.js (distancia: 0.23)
   - Similar en: semantic (auth domain)
2. /src/services/user.js (distancia: 0.31)
   - Similar en: structural (misma complejidad)
3. /src/utils/jwt.js (distancia: 0.34)
   - Similar en: lexical (términos similares)
...
```

### Caso 2: Análisis de impacto antes de refactoring

```
Usuario: "Voy a cambiar la firma de validateToken(), ¿qué se afecta?"

> cube_get_contracts path=/src/services/auth.js direction=incoming

Resultado:
Archivos que dependen de auth.js:
1. /src/routes/api.js
   - Usa: validateToken (líneas 23, 45)
   - Baseline distance: 0.28

2. /src/middleware/session.js
   - Usa: validateToken (línea 15)
   - Baseline distance: 0.31

3. /tests/auth.test.js
   - Mock: validateToken
   - Baseline distance: 0.42

Recomendación: Actualizar 3 archivos si cambia la firma.
```

### Caso 3: Detección automática de cambios rotos

```
Usuario modifica auth.js y ejecuta:

> cube_reindex path=/src/services/auth.js

Resultado:
Delta detectado:
  - Movimiento: 0.34 (significativo)
  - Cambio dominante: STRUCTURAL (+1 parámetro)

⚠️ TENSIONES DETECTADAS:

1. /src/routes/api.js
   Tensión: 0.42 (ALTA)
   Línea 23: const valid = await validateToken(req.token);
   Sugerencia: Agregar segundo parámetro

2. /src/middleware/session.js
   Tensión: 0.38 (ALTA)
   Línea 15: if (!validateToken(session.token))
   Sugerencia: Agregar segundo parámetro

Archivos estables (sin tensión):
  - /src/utils/format.js ✓
  - /src/services/email.js ✓
```

### Caso 4: Búsqueda por características específicas

```
Usuario: "Encontrar archivos con alta complejidad pero bajo acoplamiento"

> cube_find_similar
    axis=structural
    filter="cyclomatic > 0.5 AND num_imports < 0.2"

Resultado:
1. /src/utils/parser.js
   - Complejidad: 0.72
   - Imports: 0.1
   - Candidato para refactoring: código complejo pero aislado
```

---

## Plan de Implementación

### Fase 1: Cubo Básico (Prioridad: ALTA)

**Objetivo**: CodePoints funcionando con features básicas.

**Archivos a crear**:
```
src/bigcontext_mcp/cube/
├── __init__.py
├── code_point.py      # Clase CodePoint
├── features/
│   ├── __init__.py
│   ├── lexical.py     # Extractor TF-IDF
│   ├── structural.py  # Extractor regex
│   └── semantic.py    # Clasificador por dominio
└── cube.py            # Clase principal DeltaCodeCube
```

**Entregables**:
- [ ] Extractor de features léxicas (reutilizar TF-IDF)
- [ ] Extractor de features estructurales (regex)
- [ ] Extractor de features semánticas (keywords)
- [ ] Clase CodePoint
- [ ] Tabla `code_points` en DB
- [ ] Tool: `cube_index_file`
- [ ] Tool: `cube_get_position`

**Estimación**: 2-3 horas

### Fase 2: Contratos (Prioridad: ALTA)

**Objetivo**: Grafo de dependencias entre archivos.

**Archivos a crear**:
```
src/bigcontext_mcp/cube/
├── contracts.py       # Clase Contract + detector
```

**Entregables**:
- [ ] Parser de imports (regex multi-lenguaje)
- [ ] Resolver de paths relativos
- [ ] Clase Contract
- [ ] Tabla `contracts` en DB
- [ ] Cálculo de baseline_distance
- [ ] Tool: `cube_get_contracts`
- [ ] Tool: `cube_index_directory` (con contratos)

**Estimación**: 1-2 horas

### Fase 3: Deltas y Tensiones (Prioridad: MEDIA)

**Objetivo**: Detección de impacto de cambios.

**Archivos a crear**:
```
src/bigcontext_mcp/cube/
├── delta.py           # Clase Delta
├── tension.py         # Clase Tension + detector
```

**Entregables**:
- [ ] Clase Delta con análisis de movimiento
- [ ] Tabla `deltas` en DB
- [ ] Detector de tensiones
- [ ] Tabla `tensions` en DB
- [ ] Tool: `cube_reindex` (con detección)
- [ ] Tool: `cube_analyze_impact`
- [ ] Tool: `cube_get_tensions`

**Estimación**: 2-3 horas

### Fase 4: Búsqueda Avanzada (Prioridad: MEDIA)

**Objetivo**: Queries complejas en el cubo.

**Entregables**:
- [ ] Tool: `cube_find_similar` con filtros por eje
- [ ] Tool: `cube_compare`
- [ ] Tool: `cube_export_positions`

**Estimación**: 1-2 horas

### Fase 5: Sugerencias de Fix (Prioridad: BAJA)

**Objetivo**: Integración con LLM para sugerir correcciones.

**Entregables**:
- [ ] Análisis de tipo de cambio
- [ ] Generación de sugerencias
- [ ] Tool: `cube_suggest_fix`

**Estimación**: 3+ horas (requiere integración LLM)

---

## Métricas de Éxito

### Funcionales

- [ ] Indexar proyecto de 50+ archivos en < 30 segundos
- [ ] Detectar correctamente > 80% de imports
- [ ] Tensiones detectadas correlacionan con errores reales de compilación

### De Valor

- [ ] Reduce tiempo de análisis de impacto manual
- [ ] Detecta dependencias que "Find References" no encuentra
- [ ] Útil para onboarding en proyectos legacy

---

## Comparación con Alternativas

| Feature | grep/ripgrep | IDE Find Refs | TypeScript | DeltaCodeCube |
|---------|--------------|---------------|------------|---------------|
| Búsqueda léxica | ✅ Excelente | ✅ Bueno | ❌ | ✅ Bueno |
| Búsqueda estructural | ❌ | ⚠️ Limitado | ✅ AST | ✅ Heurístico |
| Búsqueda semántica | ❌ | ❌ | ❌ | ✅ Por dominio |
| Grafo dependencias | ❌ | ⚠️ Local | ✅ | ✅ |
| Detección impacto | ❌ | ❌ | ⚠️ Post-hoc | ✅ Predictivo |
| Sin config/setup | ✅ | ⚠️ | ❌ Requiere tsconfig | ✅ |
| Multi-lenguaje | ✅ | ❌ | ❌ Solo TS/JS | ✅ |

---

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Features no capturan relaciones reales | Media | Alto | Validar con proyectos reales, iterar |
| Falsos positivos en tensiones | Alta | Medio | Threshold ajustable, estado "ignored" |
| Performance con proyectos grandes | Media | Medio | Indexación incremental, caching |
| Regex no detecta todos los imports | Media | Bajo | Patterns extensibles, fallback a AST |

---

## Referencias

- [EVA4-Machine-Learning](../../../EVA4-Machine-Learning) - Concepto original de DVC Cúbico
- [bigcontext-mcp](../) - Proyecto base a extender
- TF-IDF: Salton, G. (1988). Term-weighting approaches in automatic text retrieval.

---

## Changelog

| Versión | Fecha | Cambios |
|---------|-------|---------|
| 0.1.0 | 2026-01-10 | Documento inicial de diseño |

---

*Documento generado como parte del diseño de DeltaCodeCube para bigcontext-mcp*
