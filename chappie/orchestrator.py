import asyncio
import os

from dataclasses import dataclass
from typing import Any, Protocol

from chappie.mcp_client import ChappieMCPClient
from chappie.brain.semantic import SemanticRouter
from chappie.brain.conversation import ChappieBrain
from chappie.brain.cloud import ChappieCloudBrain
from chappie.brain.state import ChappieSessionState


class MCPClientProtocol(Protocol):
    """Describe the MCP functionality required by the orchestrator."""

    async def get_system_status(
        self,
    ) -> dict[str, Any]:
        """Return current Raspberry Pi system information."""


@dataclass(frozen=True, slots=True)
class ChappieResponse:
    """A response with separate screen and speech representations."""

    display_text: str
    speech_text: str


class ChappieOrchestrator:
    """Interpret user requests and coordinate Psydekik tools."""

    SYSTEM_STATUS_PHRASES = (
        "system status",
        "pi status",
        "pie status",
        "raspberry pi",
        "raspberry pie",
        "cpu",
        "memory",
        "temperature",
        "disk space",
        "uptime",
        "how is the pi",
        "how's the pi",
        "how is the pie",
        "how's the pie",
        "how is psydekik",
        "how's psydekik",
    )

    def __init__(
        self,
        mcp_client: MCPClientProtocol,
    ) -> None:
        self.mcp_client = mcp_client

        # Lightweight conversational context.
        self._last_topic: str | None = None
        self._last_system_intent: str | None = None
        self._last_system_status: dict[str, Any] | None = None

        # Semantic fallback for natural-language system
        # requests that the deterministic router does not
        # recognize directly.
        self.semantic_router = SemanticRouter()

        # Conservative starting thresholds. A semantic
        # classification must be both strong enough and
        # clearly ahead of the runner-up.
        self.semantic_min_similarity = 0.40
        self.semantic_min_margin = 0.10

        # Persistent conversational brain. Its context
        # survives across messages handled by this
        # orchestrator instance.
        self.brain = ChappieBrain()

        self.cloud_brain: ChappieCloudBrain | None = None

        if os.getenv("OPENAI_API_KEY"):
            try:
                self.cloud_brain = ChappieCloudBrain()
                print(
                    "Cloud brain ready: "
                    f"{self.cloud_brain.model}"
                )
            except Exception as exc:
                print(
                    "Cloud brain unavailable during startup: "
                    f"{exc}"
                )

        self.state = ChappieSessionState(
            assistant_name="Chappie",
            user_name="Josh",
            platform_name="Psydekik",
        )

    async def close(self) -> None:
        """Release resources owned by the orchestrator."""

        if self.cloud_brain is not None:
            try:
                await self.cloud_brain.close()
            except Exception as exc:
                print(
                    "Cloud brain shutdown warning: "
                    f"{exc}"
                )

        try:
            await self.brain.close()
        except Exception as exc:
            print(
                "Local brain shutdown warning: "
                f"{exc}"
            )

    async def handle_message(
        self,
        message: str,
    ) -> str:
        """
        Route a message and return display text.

        This preserves compatibility with existing callers.
        """
        response = await self.handle_voice_message(
            message
        )

        return response.display_text

    async def handle_voice_message(
        self,
        message: str,
    ) -> ChappieResponse:
        """
        Route a voice request.

        Returns separate text for the screen and for speech.
        """
        normalized_message = (
            message.casefold().strip()
        )

        self.state.record_user_message(
            message
        )


        if not normalized_message:
            return ChappieResponse(
                display_text=(
                    "I didn't hear a request. "
                    "Try asking how the Pi is doing."
                ),
                speech_text=(
                    "I didn't catch that, sir."
                ),
            )

        grounded_response = (
            self._handle_grounded_state_question(
                normalized_message
            )
        )

        if grounded_response is not None:
            print("Brain route: LOCAL_STATE")
            self.state.record_assistant_message(
                grounded_response.speech_text
            )
            self.brain.remember_exchange(
                message,
                grounded_response.speech_text,
            )
            return grounded_response

        contextual_response = (
            self._handle_system_followup(
                normalized_message
            )
        )

        if contextual_response is not None:
            print("Brain route: LOCAL_SYSTEM_FOLLOWUP")
            self.state.record_assistant_message(
                contextual_response.speech_text
            )
            self.brain.remember_exchange(
                message,
                contextual_response.speech_text,
            )
            return contextual_response

        explanation_question = (
            self._is_general_explanation_question(
                normalized_message
            )
        )

        needs_web = (
            self._needs_current_web_information(
                normalized_message
            )
        )

        if needs_web:
            print(
                "System routing skipped: "
                "current web information"
            )
            system_intent = None

        elif explanation_question:
            print(
                "System routing skipped: "
                "general explanation"
            )
            system_intent = None

        else:
            system_intent = self._detect_system_intent(
                normalized_message
            )

            if system_intent is None:
                system_intent = (
                    self._detect_semantic_system_intent(
                        normalized_message
                    )
                )

        if system_intent is not None:
            print(
                "Brain route: LOCAL_SYSTEM "
                f"({system_intent})"
            )
            status = (
                await self.mcp_client.get_system_status()
            )

            self._last_topic = "system"
            self._last_system_intent = system_intent
            self._last_system_status = status

            self.state.remember_system_result(
                system_intent,
                status,
            )

            response = self._format_system_response(
                status,
                system_intent,
            )

            # The language model did not generate this
            # exchange, so explicitly place it into the
            # shared conversation history. This allows
            # natural follow-ups such as "Is that enough?"
            # or "Is that temperature okay?"
            self.state.record_assistant_message(
                response.speech_text
            )
            self.brain.remember_exchange(
                message,
                response.speech_text,
            )

            return response

        self._last_topic = "conversation"

        cloud_display_text: str | None = None
        cloud_speech_text: str | None = None

        needs_web = (
            self._needs_current_web_information(
                normalized_message
            )
        )

        if (
            needs_web
            and self.cloud_brain is not None
        ):
            try:
                print(
                    "Brain route: CLOUD_WEB "
                    f"({self.cloud_brain.model})"
                )

                cloud_response = (
                    await self.cloud_brain.respond(
                        message,
                        use_web=True,
                    )
                )

                cloud_display_text = (
                    cloud_response.display_text
                )
                cloud_speech_text = (
                    cloud_response.speech_text
                )

            except Exception as exc:
                print(
                    "Cloud web brain failed: "
                    f"{type(exc).__name__}: {exc}"
                )
                print(
                    "Falling back to normal cloud route."
                )

        if (
            cloud_display_text is None
            and self.cloud_brain is not None
        ):
            try:
                print(
                    "Brain route: CLOUD "
                    f"({self.cloud_brain.model})"
                )

                cloud_response = (
                    await self.cloud_brain.respond(
                        message
                    )
                )

                cloud_display_text = (
                    cloud_response.display_text
                )
                cloud_speech_text = (
                    cloud_response.speech_text
                )

            except Exception as exc:
                print(
                    "Cloud brain failed: "
                    f"{type(exc).__name__}: {exc}"
                )
                print(
                    "Brain route: LOCAL_FALLBACK"
                )

        if cloud_display_text is None:
            if self.cloud_brain is None:
                print(
                    "Brain route: LOCAL_FALLBACK "
                    "(cloud not configured)"
                )

            brain_response = await self.brain.respond(
                message
            )

            cloud_display_text = brain_response.text
            cloud_speech_text = brain_response.text

        if cloud_speech_text is None:
            cloud_speech_text = cloud_display_text

        response = ChappieResponse(
            display_text=cloud_display_text,
            speech_text=cloud_speech_text,
        )

        self.state.record_assistant_message(
            response.speech_text
        )

        self.brain.remember_exchange(
            message,
            response.speech_text,
        )

        return response

    def _needs_current_web_information(
        self,
        message: str,
    ) -> bool:
        """
        Return True when answering reliably requires fresh
        outside information rather than model knowledge.
        """

        message = message.casefold().strip()

        current_markers = (
            "right now",
            "currently",
            "current ",
            "current?",
            "today",
            "tonight",
            "this morning",
            "this afternoon",
            "this evening",
            "latest",
            "most recent",
            "newest",
            "recent news",
            "breaking news",
            "this week",
            "this month",
            "what happened",
            "what's happening",
            "what is happening",
        )

        web_subjects = (
            "weather",
            "forecast",
            "temperature outside",
            "news",
            "headline",
            "stock price",
            "share price",
            "market price",
            "release",
            "version",
            "score",
            "game",
            "schedule",
            "traffic",
            "flight",
            "president",
            "governor",
            "mayor",
            "ceo",
            "election",
        )

        # Weather/forecast questions inherently require
        # current information unless clearly historical.
        if (
            "weather" in message
            or "forecast" in message
        ):
            historical_markers = (
                "yesterday",
                "last year",
                "historically",
                "average weather",
                "climate",
            )

            if not any(
                marker in message
                for marker in historical_markers
            ):
                return True

        if any(
            marker in message
            for marker in current_markers
        ):
            return True

        if any(
            subject in message
            for subject in web_subjects
        ):
            freshness_words = (
                "what's",
                "what is",
                "who is",
                "when is",
                "how is",
            )

            if any(
                word in message
                for word in freshness_words
            ):
                return True

        return False

    def _is_general_explanation_question(
        self,
        message: str,
    ) -> bool:
        """
        Return True when a question is asking for a general
        explanation rather than Psydekik's current system state.

        This guard runs only before semantic fallback. Explicit
        deterministic system requests have already been handled.
        """
        message = message.casefold().strip()

        explanation_starters = (
            "why is ",
            "why does ",
            "why do ",
            "why would ",
            "why can ",
            "how does ",
            "how do ",
            "how would ",
            "explain ",
            "explain why ",
            "explain how ",
            "what causes ",
            "what makes ",
            "what is the reason ",
            "what's the reason ",
        )

        if not message.startswith(
            explanation_starters
        ):
            return False

        # Questions explicitly about THIS Pi/Psydekik should
        # still be allowed through semantic system routing.
        local_state_markers = (
            "my pi",
            "my pie",
            "the pi",
            "the pie",
            "this pi",
            "this pie",
            "psydekik",
            "bru-raspi",
            "my system",
            "this system",
            "my raspberry pi",
            "the raspberry pi",
        )

        if any(
            marker in message
            for marker in local_state_markers
        ):
            return False

        return True

    def _handle_grounded_state_question(
        self,
        message: str,
    ) -> ChappieResponse | None:
        """Answer questions whose truth lives in session state."""

        message = message.strip().lower()

        # User identity
        user_name_questions = (
            "what's my name",
            "what is my name",
            "do you know my name",
            "who am i",
        )

        if any(
            phrase in message
            for phrase in user_name_questions
        ):
            name = self.state.user_name

            return ChappieResponse(
                display_text=f"Your name is {name}.",
                speech_text=f"Your name is {name}, sir.",
            )

        # Assistant identity
        assistant_name_questions = (
            "what's your name",
            "what is your name",
            "who are you",
        )

        if any(
            phrase in message
            for phrase in assistant_name_questions
        ):
            return ChappieResponse(
                display_text=(
                    f"I'm {self.state.assistant_name}, "
                    f"the AI assistant inside "
                    f"{self.state.platform_name}."
                ),
                speech_text=(
                    f"I'm {self.state.assistant_name}, sir."
                ),
            )

        # What did the USER just say?
        previous_user_questions = (
            "what did i just tell you",
            "what did i just say",
            "what was the last thing i said",
            "what did i say before",
        )

        if any(
            phrase in message
            for phrase in previous_user_questions
        ):
            previous = self.state.previous_user_message

            if previous:
                return ChappieResponse(
                    display_text=f'You said: "{previous}"',
                    speech_text=f'You said, "{previous}"',
                )

            return ChappieResponse(
                display_text=(
                    "I don't have an earlier user "
                    "message in this session yet."
                ),
                speech_text=(
                    "I don't have an earlier message "
                    "from you in this session yet, sir."
                ),
            )

        # What did CHAPPIE just say?
        previous_assistant_questions = (
            "what did you just say",
            "what was the last thing you said",
            "what was your last response",
            "repeat what you just said",
        )

        if any(
            phrase in message
            for phrase in previous_assistant_questions
        ):
            previous = self.state.last_assistant_message

            if previous:
                return ChappieResponse(
                    display_text=previous,
                    speech_text=previous,
                )

        # Grounded temperature confirmation
        if (
            self.state.last_system_intent == "temperature"
            and "comfortable" in message
            and (
                "did you say" in message
                or "you said" in message
                or "is that" in message
                or "that's" in message
            )
        ):
            status = (
                self.state.last_system_status
                or {}
            )

            cpu = status.get("cpu", {})
            temperature = cpu.get("temperature_celsius")

            if temperature is not None:
                temperature = float(temperature)
                rounded = round(temperature)

                if temperature < 70.0:
                    judgment = "comfortable"
                elif temperature < 80.0:
                    judgment = "warm"
                else:
                    judgment = "hot"

                return ChappieResponse(
                    display_text=(
                        f"Yes. The latest CPU temperature "
                        f"is {temperature:.1f}°C, which "
                        f"I'd describe as {judgment}."
                    ),
                    speech_text=(
                        f"Yes, sir. I said it was "
                        f"{judgment}. The latest reading "
                        f"is about {rounded} degrees "
                        f"Celsius."
                    ),
                )

        return None

    def _handle_system_followup(
        self,
        message: str,
    ) -> ChappieResponse | None:
        """Answer grounded follow-ups about the latest system result."""

        if (
            self._last_system_intent is None
            or self._last_system_status is None
        ):
            return None

        intent = self._last_system_intent
        status = self._last_system_status

        # -------------------------------------------------
        # Temperature judgments
        # -------------------------------------------------

        if intent == "temperature":
            followup_phrases = (
                "is that comfortable",
                "that's comfortable",
                "that comfortable",
                "is that okay",
                "is that ok",
                "is that good",
                "should i worry",
                "is that too hot",
                "is that hot",
            )

            if any(
                phrase in message
                for phrase in followup_phrases
            ):
                cpu = status.get("cpu", {})
                temperature = cpu.get(
                    "temperature_c"
                )

                if temperature is None:
                    return None

                temperature = float(temperature)

                if temperature < 70.0:
                    judgment = (
                        "That's a comfortable operating "
                        "temperature."
                    )
                elif temperature < 80.0:
                    judgment = (
                        "That's warmer than usual, but not "
                        "immediately alarming. I'd keep an "
                        "eye on it."
                    )
                else:
                    judgment = (
                        "That's quite hot. I'd check cooling "
                        "and sustained CPU load."
                    )

                rounded = round(temperature)

                return ChappieResponse(
                    display_text=(
                        f"CPU temperature is "
                        f"{temperature:.1f}°C. "
                        f"{judgment}"
                    ),
                    speech_text=(
                        f"Yes, sir. At about {rounded} "
                        f"degrees Celsius, {judgment.lower()}"
                    ),
                )

        # -------------------------------------------------
        # Storage judgments
        # -------------------------------------------------

        if intent == "storage":
            followup_phrases = (
                "is that enough",
                "will that be enough",
                "do we have enough",
                "is that plenty",
                "are we okay on space",
                "are we good on space",
            )

            if any(
                phrase in message
                for phrase in followup_phrases
            ):
                disk = status.get("disk", {})

                free_bytes = disk.get(
                    "free_bytes"
                )

                if free_bytes is None:
                    return None

                free_gib = (
                    float(free_bytes)
                    / (1024 ** 3)
                )

                return ChappieResponse(
                    display_text=(
                        f"There are about "
                        f"{free_gib:.1f} GiB free. "
                        "That is enough for normal "
                        "Psydekik development right now, "
                        "but whether it is enough long-term "
                        "depends on what else we plan to "
                        "store."
                    ),
                    speech_text=(
                        f"We've got about "
                        f"{round(free_gib)} gigs free. "
                        "That's fine for normal Psydekik "
                        "development right now, but I'd "
                        "keep an eye on it as we add more "
                        "models and data."
                    ),
                )

        return None

    def _detect_system_intent(
        self,
        message: str,
    ) -> str | None:
        """
        Determine which part of the Pi's system status
        the user is asking about.
        """

        if any(
            phrase in message
            for phrase in (
                "temperature",
                "temp",
                "how hot",
                "running hot",
                "degrees",
            )
        ):
            return "temperature"

        if any(
            phrase in message
            for phrase in (
                "storage",
                "disk",
                "disk space",
                "space left",
                "space do i have",
                "space available",
                "free space",
                "gigs left",
                "gigabytes left",
            )
        ):
            return "storage"

        if any(
            phrase in message
            for phrase in (
                "memory",
                "ram",
                "memory usage",
                "memory left",
                "ram usage",
            )
        ):
            return "memory"

        if any(
            phrase in message
            for phrase in (
                "uptime",
                "how long has the pi been up",
                "how long has the pie been up",
                "how long has the pi been running",
                "how long has the pie been running",
            )
        ):
            return "uptime"

        if self._last_topic == "system":
            contextual_uptime_phrases = (
                "how long has it been up",
                "how long's it been up",
                "how long is it been up",
                "how long has it been running",
                "how long's it been running",
            )

            if any(
                phrase in message
                for phrase in contextual_uptime_phrases
            ):
                return "uptime"

            # Tolerate minor STT variations in contextual
            # uptime questions instead of requiring an
            # exact sentence.
            if (
                "how long" in message
                and (
                    "up" in message.split()
                    or "running" in message
                )
            ):
                return "uptime"

        if any(
            phrase in message
            for phrase in (
                "cpu",
                "processor",
                "cpu usage",
                "processor usage",
                "cpu load",
            )
        ):
            return "cpu"

        if self._requests_system_status(
            message
        ):
            return "overview"

        return None

    def _detect_semantic_system_intent(
        self,
        message: str,
    ) -> str | None:
        """
        Use local sentence embeddings as a fallback when
        deterministic system routing does not recognize
        the request.

        Reject weak or ambiguous matches rather than
        blindly choosing the nearest intent.
        """
        intent, similarity, scores = (
            self.semantic_router.classify(message)
        )

        ranked = sorted(
            scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        runner_up_similarity = (
            ranked[1][1]
            if len(ranked) > 1
            else 0.0
        )

        margin = similarity - runner_up_similarity

        if similarity < self.semantic_min_similarity:
            return None

        if margin < self.semantic_min_margin:
            return None

        return intent

    def _format_system_response(
        self,
        status: dict[str, Any],
        intent: str,
    ) -> ChappieResponse:
        """Return only the system information requested."""

        cpu = status["cpu"]
        memory = status["memory"]
        disk = status["disk"]

        if intent == "temperature":
            temperature = cpu.get(
                "temperature_celsius"
            )

            if temperature is None:
                return ChappieResponse(
                    display_text=(
                        "CPU temperature is unavailable."
                    ),
                    speech_text=(
                        "I can't read the Pi's temperature "
                        "right now, sir."
                    ),
                )

            rounded = round(temperature)

            if rounded < 65:
                speech = (
                    f"The Pi is sitting at about "
                    f"{rounded} degrees Celsius, sir. "
                    f"That's a comfortable temperature."
                )
            elif rounded < 80:
                speech = (
                    f"The Pi is at about "
                    f"{rounded} degrees Celsius, sir."
                )
            else:
                speech = (
                    f"The Pi is running hot at about "
                    f"{rounded} degrees Celsius, sir."
                )

            return ChappieResponse(
                display_text=(
                    f"CPU temperature: "
                    f"{temperature:.1f}°C."
                ),
                speech_text=speech,
            )

        if intent == "storage":
            free_disk = self._bytes_to_gib(
                disk["free_bytes"]
            )

            return ChappieResponse(
                display_text=(
                    f"Disk usage is "
                    f"{disk['usage_percent']:.1f}%, "
                    f"with {free_disk:.1f} GiB free."
                ),
                speech_text=(
                    f"You've got about "
                    f"{round(free_disk)} gigs "
                    f"of storage free, sir."
                ),
            )

        if intent == "memory":
            available_memory = self._bytes_to_gib(
                memory["available_bytes"]
            )

            return ChappieResponse(
                display_text=(
                    f"Memory usage is "
                    f"{memory['usage_percent']:.1f}%, "
                    f"with {available_memory:.1f} GiB "
                    f"available."
                ),
                speech_text=(
                    f"Memory usage is around "
                    f"{round(memory['usage_percent'])} "
                    f"percent, sir. "
                    f"You've got about "
                    f"{available_memory:.1f} gigs "
                    f"available."
                ),
            )

        if intent == "uptime":
            uptime_display = self._format_uptime(
                status["uptime_seconds"]
            )

            uptime_speech = self._format_uptime_speech(
                status["uptime_seconds"]
            )

            return ChappieResponse(
                display_text=(
                    f"Uptime is {uptime_display}."
                ),
                speech_text=(
                    f"The Pi has been up for "
                    f"{uptime_speech}, sir."
                ),
            )

        if intent == "cpu":
            cpu_usage = round(
                cpu["usage_percent"]
            )

            if cpu_usage < 20:
                description = "barely working"
            elif cpu_usage < 60:
                description = "running comfortably"
            elif cpu_usage < 85:
                description = "fairly busy"
            else:
                description = "working pretty hard"

            return ChappieResponse(
                display_text=(
                    f"CPU usage is "
                    f"{cpu['usage_percent']:.1f}%."
                ),
                speech_text=(
                    f"The CPU is {description} "
                    f"at around {cpu_usage} percent, sir."
                ),
            )

        return ChappieResponse(
            display_text=(
                self._format_system_status_display(
                    status
                )
            ),
            speech_text=(
                self._format_system_status_speech(
                    status
                )
            ),
        )

    def _requests_system_status(
        self,
        message: str,
    ) -> bool:
        """Determine whether a message requests system information."""
        return any(
            phrase in message
            for phrase in self.SYSTEM_STATUS_PHRASES
        )

    def _format_system_status_display(
        self,
        status: dict[str, Any],
    ) -> str:
        """Create the detailed screen representation."""
        cpu = status["cpu"]
        memory = status["memory"]
        disk = status["disk"]

        uptime = self._format_uptime(
            status["uptime_seconds"]
        )

        available_memory = self._bytes_to_gib(
            memory["available_bytes"]
        )

        free_disk = self._bytes_to_gib(
            disk["free_bytes"]
        )

        temperature = cpu.get(
            "temperature_celsius"
        )

        temperature_text = (
            f"{temperature:.1f}°C"
            if temperature is not None
            else "unavailable"
        )

        return (
            f"{status['hostname']} is online. "
            f"CPU usage is "
            f"{cpu['usage_percent']:.1f}% at "
            f"{temperature_text}. "
            f"Memory usage is "
            f"{memory['usage_percent']:.1f}%, with "
            f"{available_memory:.1f} GiB available. "
            f"Disk usage is "
            f"{disk['usage_percent']:.1f}%, with "
            f"{free_disk:.1f} GiB free. "
            f"Uptime is {uptime}."
        )

    def _format_system_status_speech(
        self,
        status: dict[str, Any],
    ) -> str:
        """
        Interpret system telemetry and turn it into short,
        natural sentences optimized for local TTS.
        """
        cpu = status["cpu"]
        memory = status["memory"]
        disk = status["disk"]

        cpu_usage = round(
            cpu["usage_percent"]
        )

        memory_usage = round(
            memory["usage_percent"]
        )

        disk_usage = round(
            disk["usage_percent"]
        )

        free_disk = round(
            self._bytes_to_gib(
                disk["free_bytes"]
            )
        )

        temperature = cpu.get(
            "temperature_celsius"
        )

        temperature_rounded = (
            round(temperature)
            if temperature is not None
            else None
        )

        sentences: list[str] = []

        if (
            temperature is not None
            and temperature >= 80
        ):
            sentences.append(
                "The Pi is online, sir."
            )

            sentences.append(
                "It is running hotter than I'd like."
            )

        elif (
            disk_usage >= 90
            or memory_usage >= 90
            or cpu_usage >= 90
        ):
            sentences.append(
                "The Pi is online, sir."
            )

            sentences.append(
                "There is something worth watching."
            )

        else:
            sentences.append(
                "Everything looks good, sir."
            )

            sentences.append(
                "The Pi is online and responding normally."
            )

            sentences.append(
                "Nothing needs your attention right now."
            )

        if cpu_usage < 20:
            sentences.append(
                f"CPU is barely working at around "
                f"{cpu_usage} percent."
            )

        elif cpu_usage < 60:
            sentences.append(
                f"CPU is sitting comfortably at around "
                f"{cpu_usage} percent."
            )

        elif cpu_usage < 85:
            sentences.append(
                f"CPU is fairly busy at around "
                f"{cpu_usage} percent."
            )

        else:
            sentences.append(
                f"CPU is working pretty hard at around "
                f"{cpu_usage} percent."
            )

        if temperature_rounded is not None:
            if temperature_rounded < 65:
                sentences.append(
                    f"Temperature is a comfortable "
                    f"{temperature_rounded} degrees Celsius."
                )

            elif temperature_rounded < 80:
                sentences.append(
                    f"Temperature is "
                    f"{temperature_rounded} degrees Celsius."
                )

            else:
                sentences.append(
                    f"Temperature is running hot at "
                    f"{temperature_rounded} degrees Celsius."
                )

        if memory_usage < 70:
            sentences.append(
                f"Memory is only around "
                f"{memory_usage} percent."
            )

        elif memory_usage < 85:
            sentences.append(
                f"Memory is sitting at about "
                f"{memory_usage} percent."
            )

        else:
            sentences.append(
                f"Memory usage is getting high at about "
                f"{memory_usage} percent."
            )

        if free_disk >= 20:
            sentences.append(
                f"You've still got about "
                f"{free_disk} gigs of storage free."
            )

        elif free_disk >= 10:
            sentences.append(
                f"Storage is getting a little tight."
            )

            sentences.append(
                f"You've got about "
                f"{free_disk} gigs free."
            )

        else:
            sentences.append(
                "Storage is getting low."
            )

            sentences.append(
                f"You've only got about "
                f"{free_disk} gigs free."
            )

        uptime_speech = self._format_uptime_speech(
            status["uptime_seconds"]
        )

        sentences.append(
            f"It's been up for {uptime_speech}."
        )

        return " ".join(sentences)

    @staticmethod
    def _bytes_to_gib(
        byte_count: int,
    ) -> float:
        """Convert bytes to gibibytes."""
        return byte_count / (1024**3)

    @staticmethod
    def _format_uptime(
        total_seconds: int,
    ) -> str:
        """Format uptime for detailed display."""
        days, remainder = divmod(
            total_seconds,
            86_400,
        )

        hours, remainder = divmod(
            remainder,
            3_600,
        )

        minutes, _ = divmod(
            remainder,
            60,
        )

        parts: list[str] = []

        if days:
            parts.append(
                f"{days} "
                f"day{'s' if days != 1 else ''}"
            )

        if hours:
            parts.append(
                f"{hours} "
                f"hour{'s' if hours != 1 else ''}"
            )

        if minutes or not parts:
            parts.append(
                f"{minutes} "
                f"minute{'s' if minutes != 1 else ''}"
            )

        return ", ".join(parts)

    @staticmethod
    def _format_uptime_speech(
        total_seconds: int,
    ) -> str:
        """Create a shorter uptime phrase for spoken responses."""
        days, remainder = divmod(
            total_seconds,
            86_400,
        )

        hours, _ = divmod(
            remainder,
            3_600,
        )

        if days and hours:
            return (
                f"{days} "
                f"day{'s' if days != 1 else ''} "
                f"and {hours} "
                f"hour{'s' if hours != 1 else ''}"
            )

        if days:
            return (
                f"{days} "
                f"day{'s' if days != 1 else ''}"
            )

        if hours:
            return (
                f"{hours} "
                f"hour{'s' if hours != 1 else ''}"
            )

        return "less than an hour"


async def main() -> None:
    """Run a single conversational Psydekik request."""
    async with ChappieMCPClient() as mcp_client:
        orchestrator = ChappieOrchestrator(
            mcp_client
        )

        message = input(
            "You: "
        )

        response = (
            await orchestrator.handle_voice_message(
                message
            )
        )

        print(
            f"Chappie: {response.display_text}"
        )

        print(
            f"Speech:  {response.speech_text}"
        )


if __name__ == "__main__":
    asyncio.run(main())
