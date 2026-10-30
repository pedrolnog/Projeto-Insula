"""Cliente Mock do Sienge para desenvolvimento e testes sem necessidade de credenciais ativas."""
import io
from datetime import date, datetime, timedelta

from PIL import Image, ImageDraw

from app.clients.sienge.base import Json, SiengeClient

_DIAS_SEMANA = (
    "Segunda-feira",
    "Terça-feira",
    "Quarta-feira",
    "Quinta-feira",
    "Sexta-feira",
    "Sábado",
    "Domingo",
)


class MockSiengeClient(SiengeClient):
    """Simula as respostas do ERP Sienge em memória com dados coerentes com a OpenAPI."""

    def __init__(self) -> None:
        super().__init__()
        self._hoje = date.today()
        self._datas_por_diario: dict[tuple[int, int], date] = {}

    # --- Empreendimentos -------------------------------------------------
    async def listar_empreendimentos(self) -> list[Json]:
        self.requisicoes += 1
        return [
            {
                "id": 101,
                "name": "Residencial Gran Benedetto",
                "commercialName": "Gran Benedetto Residence",
                "enterpriseObservation": "Obra residencial de alto padrão a preço de custo",
                "cnpj": "12345678000199",
                "type": "RESIDENTIAL",
                "adress": "Av. Beira Mar, 1000 - Meireles, Fortaleza - CE",
                "creationDate": "2024-01-10T10:00:00",
                "modificationDate": "2024-06-01T15:30:00",
                "companyId": 1,
                "companyName": "Benedetto Engenharia & Incorporações",
                "buildingTypeId": 10,
                "buildingTypeDescription": "Edifício Residencial",
            },
            {
                "id": 102,
                "name": "Condomínio Villa Di Fiori",
                "commercialName": "Villa Di Fiori Casas",
                "enterpriseObservation": "Condomínio horizontal com 40 casas",
                "cnpj": "12345678000288",
                "type": "RESIDENTIAL",
                "adress": "Rua das Flores, 500 - Eusébio - CE",
                "creationDate": "2024-02-15T09:00:00",
                "modificationDate": "2024-05-20T11:00:00",
                "companyId": 1,
                "companyName": "Benedetto Engenharia & Incorporações",
                "buildingTypeId": 20,
                "buildingTypeDescription": "Condomínio Horizontal",
            },
        ]

    # --- Diário de Obra --------------------------------------------------
    async def listar_diarios(self, building_id: int, inicio: date, fim: date) -> list[Json]:
        self.requisicoes += 1
        diarios: list[Json] = []
        delta_dias = (fim - inicio).days
        for i in range(max(0, delta_dias + 1)):
            data_corrente = inicio + timedelta(days=i)
            if data_corrente.weekday() >= 6:  # Pula domingos
                continue
            diario_id = (building_id * 1000) + (
                data_corrente.year * 10000 + data_corrente.month * 100 + data_corrente.day
            ) % 1000
            self._datas_por_diario[(building_id, diario_id)] = data_corrente
            diarios.append(
                {
                    "id": diario_id,
                    "buildingId": building_id,
                    "date": data_corrente.isoformat(),
                    "responsibleId": "ENG_RESPONSAVEL",
                    "shifts": [
                        {
                            "description": "Diurno",
                            "startTime": "07:30",
                            "finishTime": "17:00",
                            "weatherCondition": "Ensolarado",
                        }
                    ],
                }
            )
        return diarios

    async def obter_diario(self, building_id: int, diario_id: int) -> Json:
        self.requisicoes += 1
        data_obj = self._datas_por_diario.get((building_id, diario_id), self._hoje - timedelta(days=1))
        data_diario = data_obj.isoformat()
        dia_semana = _DIAS_SEMANA[data_obj.weekday()]
        return {
            "id": diario_id,
            "buildingId": building_id,
            "date": data_diario,
            "weekDay": dia_semana,
            "responsibleId": "ENG_BENEDETTO",
            "notes": (
                "Concretagem da laje do 4º pavimento realizada com sucesso conforme ensaios de abatimento (slump test). "
                "Início das instalações hidrossanitárias no 2º pavimento e montagem de fôrmas do 5º pavimento."
            ),
            "rainfallIndex": 0.0,
            "createdAt": f"{data_diario}T17:30:00",
            "modifiedAt": f"{data_diario}T18:15:00",
            "shifts": [
                {
                    "description": "Manhã",
                    "startTime": "07:30",
                    "finishTime": "12:00",
                    "weatherCondition": "Bom",
                },
                {
                    "description": "Tarde",
                    "startTime": "13:00",
                    "finishTime": "17:30",
                    "weatherCondition": "Bom",
                },
            ],
            "plannedTasks": [
                {
                    "id": 1,
                    "buildingUnitId": 1,
                    "taskId": 101,
                    "notes": "Laje concretada com FCK 30 MPa",
                    "quantity": 120.5,
                    "unitOfMeasure": "m3",
                    "supplierId": 45,
                    "siteId": building_id,
                },
                {
                    "id": 2,
                    "buildingUnitId": 1,
                    "taskId": 102,
                    "notes": "Alvenaria de vedação dos blocos cerâmicos",
                    "quantity": 85.0,
                    "unitOfMeasure": "m2",
                    "supplierId": 12,
                    "siteId": building_id,
                },
            ],
            "detachedTasks": [
                {
                    "id": 3,
                    "description": "Limpeza e descarte de entulho no canteiro",
                    "notes": "Caçamba 04 recolhida pela transportadora",
                    "quantity": 1.0,
                    "unitOfMeasure": "un",
                    "siteId": building_id,
                }
            ],
            "events": [
                {
                    "id": 901,
                    "description": "Visita do projetista estrutural para vistoria de ferragens",
                    "eventTypeId": 1,
                    "eventTypeDescription": "Visitas Técnicas",
                }
            ],
            "crews": [
                {
                    "id": 501,
                    "resourceId": 10,
                    "description": "Pedreiros",
                    "quantity": 12,
                    "crewTypeId": 1,
                    "origin": "type",
                    "assignment": "DIRECT_LABOR",
                },
                {
                    "id": 502,
                    "resourceId": 11,
                    "description": "Ajudantes",
                    "quantity": 18,
                    "crewTypeId": 1,
                    "origin": "type",
                    "assignment": "DIRECT_LABOR",
                },
            ],
            "equipments": [
                {
                    "id": 601,
                    "resourceId": 21,
                    "description": "Bomba de concreto estacionária",
                    "quantity": 1,
                    "equipmentTypeId": 2,
                    "origin": "resource",
                    "status": "OPERATIONAL",
                }
            ],
            "attachments": [
                {
                    "attachmentNumber": 1,
                    "name": "concretagem_laje_04.jpg",
                    "description": "Concretagem da laje do 4º pavimento",
                    "location": "Torre A - 4º Pavimento",
                },
                {
                    "attachmentNumber": 2,
                    "name": "alvenaria_bloco_a.jpg",
                    "description": "Alvenaria do 2º pavimento em execução",
                    "location": "Torre A - 2º Pavimento",
                },
            ],
        }

    async def baixar_anexo(self, building_id: int, diario_id: int, attachment_number: int) -> bytes:
        self.requisicoes += 1
        img = Image.new(
            "RGB",
            (1280, 720),
            color=(30, 60, 90) if attachment_number == 1 else (60, 90, 60),
        )
        draw = ImageDraw.Draw(img)
        draw.text(
            (50, 50),
            f"Sienge Mock Photo - Obra {building_id} - Diario {diario_id} - Anexo {attachment_number}",
            fill=(255, 255, 255),
        )
        draw.text(
            (50, 100),
            f"Gerado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            fill=(200, 200, 200),
        )
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        return buffer.getvalue()

    # --- Planejamento ----------------------------------------------------
    async def listar_tarefas_planejamento(self, building_id: int, building_unit_id: int) -> list[Json]:
        self.requisicoes += 1
        return [
            {
                "id": 101,
                "presentationId": 1,
                "description": "Estrutura de Concreto Armado",
                "level": 2,
                "startDate": "2024-03-01",
                "finishDate": "2024-11-30",
                "duration": 270,
                "summary": False,
                "unitOfMeasure": "m3",
                "quantity": 1800.0,
            },
            {
                "id": 102,
                "presentationId": 2,
                "description": "Alvenaria e Vedações",
                "level": 2,
                "startDate": "2024-05-15",
                "finishDate": "2025-02-28",
                "duration": 280,
                "summary": False,
                "unitOfMeasure": "m2",
                "quantity": 5600.0,
            },
            {
                "id": 103,
                "presentationId": 3,
                "description": "Instalações Hidrossanitárias",
                "level": 2,
                "startDate": "2024-06-01",
                "finishDate": "2025-04-30",
                "duration": 330,
                "summary": False,
                "unitOfMeasure": "un",
                "quantity": 120.0,
            },
        ]

    async def listar_medicoes(self, building_id: int) -> list[Json]:
        self.requisicoes += 1
        return [
            {
                "buildingId": building_id,
                "measurementNumber": 1,
                "date": "2024-08-31",
                "responsibleId": "ENG_BENEDETTO",
                "responsibleName": "Engenheiro Responsável",
                "consistent": True,
                "statusApproval": "APROVADA",
            },
            {
                "buildingId": building_id,
                "measurementNumber": 2,
                "date": "2024-09-30",
                "responsibleId": "ENG_BENEDETTO",
                "responsibleName": "Engenheiro Responsável",
                "consistent": True,
                "statusApproval": "APROVADA",
            },
        ]

    async def obter_medicao(self, building_id: int, measurement_number: int) -> Json:
        self.requisicoes += 1
        return {
            "buildingId": building_id,
            "measurementNumber": measurement_number,
            "date": "2024-09-30",
            "responsibleId": "ENG_BENEDETTO",
            "responsibleName": "Engenheiro Responsável",
            "consistent": True,
            "statusApproval": "APROVADA",
            "notes": "Medição física referente ao mês de Setembro/2024",
            "buildingUnits": [
                {"id": 1, "description": "Torre A"},
                {"id": 2, "description": "Área Comum / Lazer"},
            ],
        }

    async def listar_itens_medicao(
        self, building_id: int, measurement_number: int, building_unit_id: int
    ) -> list[Json]:
        self.requisicoes += 1
        return [
            {
                "taskId": 101,
                "presentationId": 1,
                "summary": False,
                "description": "Estrutura de Concreto Armado",
                "unitOfMeasurement": "m3",
                "plannedQuantity": 1800.0,
                "measuredQuantity": 180.0,
                "unitPrice": 550.0,
                "cumulativeMeasuredQuantity": 1080.0,
                "cumulativePercentage": 60.0,
            },
            {
                "taskId": 102,
                "presentationId": 2,
                "summary": False,
                "description": "Alvenaria e Vedações",
                "unitOfMeasurement": "m2",
                "plannedQuantity": 5600.0,
                "measuredQuantity": 840.0,
                "unitPrice": 120.0,
                "cumulativeMeasuredQuantity": 1680.0,
                "cumulativePercentage": 30.0,
            },
        ]
